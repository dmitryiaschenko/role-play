import asyncio
from typing import AsyncGenerator, Callable
from google.cloud import speech
from app.config import SAMPLE_RATE, STT_LANGUAGE_CODE


class StreamingSpeechToText:
    """Handles streaming speech-to-text using Google Cloud Speech API."""

    def __init__(self):
        self.client = speech.SpeechClient()
        self.config = speech.RecognitionConfig(
            encoding=speech.RecognitionConfig.AudioEncoding.LINEAR16,
            sample_rate_hertz=SAMPLE_RATE,
            language_code=STT_LANGUAGE_CODE,
            enable_automatic_punctuation=True,
            model="latest_long",
        )
        self.streaming_config = speech.StreamingRecognitionConfig(
            config=self.config,
            interim_results=True,
            single_utterance=False,
        )

    async def transcribe_stream(
        self,
        audio_generator: AsyncGenerator[bytes, None],
        on_interim: Callable[[str], None] = None,
        on_final: Callable[[str, bool], None] = None,
    ) -> None:
        """
        Transcribe audio from an async generator.

        Args:
            audio_generator: Async generator yielding audio chunks
            on_interim: Callback for interim (partial) transcriptions
            on_final: Callback for final transcriptions (text, is_end_of_utterance)
        """

        def request_generator():
            # First request must contain the config
            yield speech.StreamingRecognizeRequest(streaming_config=self.streaming_config)

            # Create a queue to receive audio chunks from the async generator
            audio_queue = asyncio.Queue()

            async def fill_queue():
                async for chunk in audio_generator:
                    await audio_queue.put(chunk)
                await audio_queue.put(None)  # Signal end

            # This won't work directly - we need to bridge async and sync
            # Using a different approach below

        # Bridge async generator to sync for Google's streaming API
        audio_buffer = []
        buffer_event = asyncio.Event()
        stop_flag = False

        async def collect_audio():
            nonlocal stop_flag
            async for chunk in audio_generator:
                if stop_flag:
                    break
                audio_buffer.append(chunk)
                buffer_event.set()
            stop_flag = True
            buffer_event.set()

        def sync_audio_generator():
            yield speech.StreamingRecognizeRequest(streaming_config=self.streaming_config)

            while True:
                if audio_buffer:
                    chunk = audio_buffer.pop(0)
                    yield speech.StreamingRecognizeRequest(audio_content=chunk)
                elif stop_flag:
                    break
                else:
                    # Small sleep to wait for more audio
                    import time
                    time.sleep(0.01)

        # Start collecting audio in background
        collect_task = asyncio.create_task(collect_audio())

        try:
            # Run the streaming recognition in a thread pool
            loop = asyncio.get_event_loop()
            responses = await loop.run_in_executor(
                None,
                lambda: list(self.client.streaming_recognize(sync_audio_generator()))
            )

            for response in responses:
                for result in response.results:
                    transcript = result.alternatives[0].transcript

                    if result.is_final:
                        if on_final:
                            # Check if this marks end of speech
                            is_end = (
                                result.result_end_time is not None and
                                hasattr(response, 'speech_event_type')
                            )
                            on_final(transcript, is_end)
                    else:
                        if on_interim:
                            on_interim(transcript)

        finally:
            stop_flag = True
            collect_task.cancel()
            try:
                await collect_task
            except asyncio.CancelledError:
                pass


class SimpleStreamingSTT:
    """
    Simplified streaming STT that processes audio chunks and returns results.
    Better suited for WebSocket-based real-time processing.
    """

    def __init__(self):
        self.client = speech.SpeechClient()
        self._stream = None
        self._audio_queue = asyncio.Queue()
        self._is_running = False

    def get_config(self):
        return speech.StreamingRecognitionConfig(
            config=speech.RecognitionConfig(
                encoding=speech.RecognitionConfig.AudioEncoding.LINEAR16,
                sample_rate_hertz=SAMPLE_RATE,
                language_code=STT_LANGUAGE_CODE,
                enable_automatic_punctuation=True,
            ),
            interim_results=True,
            single_utterance=False,
        )

    async def start(self):
        """Start a new streaming session."""
        self._is_running = True
        self._audio_queue = asyncio.Queue()

    async def stop(self):
        """Stop the streaming session."""
        self._is_running = False
        await self._audio_queue.put(None)

    async def add_audio(self, chunk: bytes):
        """Add an audio chunk to be transcribed."""
        if self._is_running:
            await self._audio_queue.put(chunk)

    def _generate_requests(self):
        """Generate streaming requests for the Speech API."""
        yield speech.StreamingRecognizeRequest(streaming_config=self.get_config())

        while self._is_running:
            try:
                # Use a timeout to allow checking is_running
                chunk = self._audio_queue.get_nowait()
                if chunk is None:
                    break
                yield speech.StreamingRecognizeRequest(audio_content=chunk)
            except asyncio.QueueEmpty:
                import time
                time.sleep(0.01)

    async def process_responses(self) -> AsyncGenerator[dict, None]:
        """
        Process streaming responses and yield transcription results.

        Yields:
            dict with keys:
                - transcript: The transcribed text
                - is_final: Whether this is a final result
                - confidence: Confidence score (for final results)
        """
        loop = asyncio.get_event_loop()

        def run_streaming():
            results = []
            try:
                responses = self.client.streaming_recognize(self._generate_requests())
                for response in responses:
                    for result in response.results:
                        if result.alternatives:
                            results.append({
                                "transcript": result.alternatives[0].transcript,
                                "is_final": result.is_final,
                                "confidence": result.alternatives[0].confidence if result.is_final else None,
                            })
            except Exception as e:
                results.append({"error": str(e)})
            return results

        # Run in thread pool since Google's API is synchronous
        results = await loop.run_in_executor(None, run_streaming)

        for result in results:
            yield result
