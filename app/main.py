import asyncio
import json
import base64
import logging
from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from fastapi.requests import Request
from fastapi.responses import JSONResponse

from app.services.speech_to_text import SimpleStreamingSTT
from app.services.text_to_speech import TextToSpeech
from app.services.gemini import GeminiChat
from app.characters import get_character, list_characters, Character
from app.conversation import ConversationManager, ConversationState

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = FastAPI(title="Role-Play Demo")

# Mount static files and templates
app.mount("/static", StaticFiles(directory="static"), name="static")
templates = Jinja2Templates(directory="templates")


@app.get("/")
async def home(request: Request):
    """Serve the main page."""
    return templates.TemplateResponse("index.html", {
        "request": request,
        "characters": list_characters(),
    })


@app.get("/api/characters")
async def get_characters():
    """Get list of available characters."""
    return JSONResponse(content=list_characters())


class ConversationSession:
    """Manages a single WebSocket conversation session."""

    def __init__(self, websocket: WebSocket, character: Character):
        self.websocket = websocket
        self.character = character
        self.manager = ConversationManager()
        self.gemini = GeminiChat(system_prompt=character.system_prompt)
        self.tts = TextToSpeech()
        self.stt = SimpleStreamingSTT()
        self._audio_buffer = []
        self._is_running = False
        self._speech_timeout_task = None
        self._last_speech_time = None

    async def send_message(self, msg_type: str, data: dict = None):
        """Send a JSON message to the client."""
        message = {"type": msg_type}
        if data:
            message.update(data)
        await self.websocket.send_json(message)

    async def send_audio(self, audio_bytes: bytes):
        """Send audio data to the client."""
        audio_b64 = base64.b64encode(audio_bytes).decode("utf-8")
        await self.send_message("audio", {"audio": audio_b64})

    async def handle_audio_chunk(self, audio_data: bytes):
        """Handle incoming audio chunk from the client."""
        if self.manager.state == ConversationState.SPEAKING:
            # User is speaking while AI is talking - interrupt!
            await self.manager.interrupt()
            await self.send_message("interrupted")
            return

        if self.manager.state != ConversationState.LISTENING:
            return

        self._audio_buffer.append(audio_data)

        # Log every 10th chunk to reduce noise
        if len(self._audio_buffer) % 10 == 0:
            logger.info(f"Audio buffer: {len(self._audio_buffer)} chunks")

        # Process after collecting ~3 seconds of audio (12 chunks at 250ms each)
        # Only start processing task once, don't keep restarting it
        if len(self._audio_buffer) >= 12 and self._speech_timeout_task is None:
            logger.info(f"Starting speech processing task... (buffer={len(self._audio_buffer)}, task={self._speech_timeout_task})")
            self._speech_timeout_task = asyncio.create_task(
                self._process_and_reset()
            )

    async def _process_and_reset(self):
        """Process speech and reset for next turn."""
        # Small delay to collect any final chunks
        await asyncio.sleep(0.3)

        if self._audio_buffer and self.manager.state == ConversationState.LISTENING:
            await self._process_speech()

        # Reset the task so we can process again
        self._speech_timeout_task = None

    async def _process_speech(self):
        """Process accumulated speech and generate response."""
        if not self._audio_buffer:
            logger.info("No audio in buffer, skipping processing")
            return

        # Combine audio chunks
        combined_audio = b"".join(self._audio_buffer)
        logger.info(f"Processing speech: {len(combined_audio)} bytes from {len(self._audio_buffer)} chunks")
        self._audio_buffer = []

        await self.send_message("state", {"state": "processing"})
        await self.manager.set_state(ConversationState.PROCESSING)

        try:
            # For simplicity, using non-streaming STT here
            # In production, you'd use the streaming API
            from google.cloud import speech

            client = speech.SpeechClient()
            audio = speech.RecognitionAudio(content=combined_audio)
            config = speech.RecognitionConfig(
                encoding=speech.RecognitionConfig.AudioEncoding.WEBM_OPUS,
                sample_rate_hertz=48000,
                language_code="en-US",
                enable_automatic_punctuation=True,
            )

            logger.info("Sending audio to Google Speech-to-Text...")
            response = client.recognize(config=config, audio=audio)
            logger.info(f"Got {len(response.results)} results from STT")

            transcript = ""
            for result in response.results:
                transcript += result.alternatives[0].transcript

            logger.info(f"Transcript: '{transcript}'")

            if transcript.strip():
                await self.send_message("transcript", {"text": transcript, "is_final": True})
                await self._generate_response(transcript)
            else:
                logger.info("Empty transcript, returning to listening")
                await self.manager.set_state(ConversationState.LISTENING)
                await self.send_message("state", {"state": "listening"})

        except Exception as e:
            logger.error(f"Speech processing error: {e}")
            await self.send_message("error", {"message": str(e)})
            await self.manager.set_state(ConversationState.LISTENING)
            await self.send_message("state", {"state": "listening"})

    async def _generate_response(self, user_message: str):
        """Generate AI response and send as audio."""
        logger.info(f"Generating response for: '{user_message}'")
        await self.manager.update_transcript(user_message, is_final=True)

        try:
            # Get response from Gemini
            logger.info("Calling Gemini...")
            full_response = ""
            async for chunk in self.gemini.send_message_stream(user_message):
                if self.manager.is_interrupted:
                    break
                full_response += chunk
                await self.send_message("response_chunk", {"text": chunk})
            logger.info(f"Gemini response: '{full_response[:100]}...' ({len(full_response)} chars)")

            if self.manager.is_interrupted:
                return

            if full_response.strip():
                await self.manager.add_response(full_response)
                await self.send_message("response", {"text": full_response})
                logger.info("Sent response text to client")

                # Convert to speech
                await self.manager.start_speaking()
                await self.send_message("state", {"state": "speaking"})
                logger.info("Starting TTS...")

                audio_bytes = self.tts.synthesize(
                    full_response,
                    voice_name=self.character.voice_name,
                    speaking_rate=self.character.speaking_rate,
                    pitch=self.character.pitch,
                )
                logger.info(f"TTS complete: {len(audio_bytes)} bytes")

                if not self.manager.is_interrupted:
                    await self.send_audio(audio_bytes)
                    logger.info("Audio sent to client")

                await self.manager.finish_speaking()

            await self.send_message("state", {"state": "listening"})
            await self.manager.set_state(ConversationState.LISTENING)
            logger.info("Ready for next input")

        except Exception as e:
            logger.error(f"Error in _generate_response: {e}", exc_info=True)
            await self.send_message("error", {"message": str(e)})
            await self.manager.set_state(ConversationState.LISTENING)
            await self.send_message("state", {"state": "listening"})

    async def start(self):
        """Start the conversation session."""
        self._is_running = True
        await self.manager.start_listening()
        await self.send_message("state", {"state": "listening"})
        await self.send_message("character", {
            "name": self.character.name,
            "description": self.character.description,
        })

    async def stop(self):
        """Stop the conversation session."""
        self._is_running = False
        if self._speech_timeout_task:
            self._speech_timeout_task.cancel()
        await self.manager.stop()

    async def generate_assessment(self):
        """Generate a coaching assessment of the student's sales pitch."""
        history = self.manager.get_history_for_display()

        if len(history) < 2:
            return None

        # Build conversation transcript
        transcript = "\n".join([
            f"{'Seller' if turn['role'] == 'user' else 'Buyer'}: {turn['text']}"
            for turn in history
        ])

        assessment_prompt = f"""You are a sales coach evaluating a student's value-based selling practice session.

The student was practicing selling to a buyer (Operations Manager at a cleaning services company who currently uses metal paper clips).

Here is the conversation transcript:
---
{transcript}
---

Please provide a coaching assessment with the following sections:

1. **Overall Score**: Rate the pitch from 1-10

2. **Summary**: Brief 2-3 sentence summary of how the conversation went

3. **Strongest Points**:
   - List 2-3 things the student did well
   - Be specific with examples from the conversation

4. **Areas for Improvement**:
   - List 2-3 things the student could improve
   - Provide specific suggestions

5. **Key Opportunities Missed**:
   - Did the student uncover the buyer's pain points? (rust issues, paper costs, shredder damage, employee injuries)
   - Did they quantify the value/ROI?
   - Did they ask open-ended questions?

6. **One Key Tip**: The single most important thing to focus on next time

Keep the feedback constructive and encouraging. Format it nicely for display."""

        # Use a fresh Gemini instance for assessment
        assessment_gemini = GeminiChat(system_prompt="You are an expert sales coach providing constructive feedback.")

        try:
            response = assessment_gemini.send_message(assessment_prompt)
            return response
        except Exception as e:
            logger.error(f"Error generating assessment: {e}")
            return None


@app.websocket("/ws/conversation/{character_id}")
async def websocket_conversation(websocket: WebSocket, character_id: str):
    """WebSocket endpoint for real-time conversation."""
    await websocket.accept()
    logger.info(f"WebSocket connected for character: {character_id}")

    character = get_character(character_id)
    session = ConversationSession(websocket, character)

    try:
        await session.start()

        while True:
            # Receive message from client
            message = await websocket.receive()
            logger.info(f"Received message type: {message.get('type')}")

            if message["type"] == "websocket.disconnect":
                break

            if "bytes" in message:
                # Ignore audio data - we're using browser's Web Speech API now
                pass

            elif "text" in message:
                # JSON message
                data = json.loads(message["text"])
                logger.info(f"Received JSON: {data.get('type')}")

                if data.get("type") == "stop":
                    # Generate assessment before stopping
                    logger.info("Generating assessment...")

                    assessment = await session.generate_assessment()

                    if assessment:
                        await session.send_message("assessment", {"text": assessment})
                        logger.info("Assessment sent to client")
                    else:
                        # No assessment (not enough conversation)
                        await session.send_message("assessment", {"text": "Not enough conversation to generate an assessment. Try having a longer sales conversation next time!"})

                    await session.stop()
                    break

                elif data.get("type") == "change_character":
                    new_character_id = data.get("character_id")
                    character = get_character(new_character_id)
                    session.character = character
                    session.gemini.set_character(character.system_prompt)
                    await session.send_message("character", {
                        "name": character.name,
                        "description": character.description,
                    })

                elif data.get("type") == "text_message":
                    text = data.get("text", "")
                    logger.info(f"Processing text message: '{text}'")
                    if text.strip():
                        await session._generate_response(text)

    except WebSocketDisconnect:
        logger.info("WebSocket disconnected")
    except Exception as e:
        logger.error(f"WebSocket error: {e}")
        try:
            await websocket.send_json({"type": "error", "message": str(e)})
        except Exception:
            pass
    finally:
        await session.stop()


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
