import google.generativeai as genai
from typing import AsyncGenerator, List, Dict
from app.config import GOOGLE_API_KEY


class GeminiChat:
    """Handles chat interactions with Google Gemini API."""

    def __init__(self, system_prompt: str = None):
        """
        Initialize Gemini chat.

        Args:
            system_prompt: The system prompt defining the character/behavior
        """
        genai.configure(api_key=GOOGLE_API_KEY)

        self.model = genai.GenerativeModel(
            model_name="gemini-3-pro-preview",
            system_instruction=system_prompt,
        )
        self.chat = self.model.start_chat(history=[])
        self.system_prompt = system_prompt

    def reset_conversation(self):
        """Reset the conversation history."""
        self.chat = self.model.start_chat(history=[])

    def set_character(self, system_prompt: str):
        """Change the character/system prompt and reset conversation."""
        self.system_prompt = system_prompt
        self.model = genai.GenerativeModel(
            model_name="gemini-3-pro-preview",
            system_instruction=system_prompt,
        )
        self.reset_conversation()

    def send_message(self, message: str) -> str:
        """
        Send a message and get a response.

        Args:
            message: User's message

        Returns:
            AI's response text
        """
        response = self.chat.send_message(message)
        return response.text

    async def send_message_stream(self, message: str) -> AsyncGenerator[str, None]:
        """
        Send a message and stream the response.

        Args:
            message: User's message

        Yields:
            Chunks of the response text
        """
        response = self.chat.send_message(message, stream=True)

        for chunk in response:
            if chunk.text:
                yield chunk.text

    def get_history(self) -> List[Dict[str, str]]:
        """Get the conversation history."""
        history = []
        for message in self.chat.history:
            history.append({
                "role": message.role,
                "content": message.parts[0].text if message.parts else "",
            })
        return history


# Default system prompt for a helpful assistant
DEFAULT_SYSTEM_PROMPT = """You are a helpful AI assistant engaged in a voice conversation.
Keep your responses concise and natural for spoken dialogue.
Avoid using markdown formatting, lists, or special characters that don't work well when spoken.
Respond conversationally as if having a real-time chat."""
