import asyncio
from enum import Enum
from dataclasses import dataclass, field
from typing import Optional, Callable, List
from datetime import datetime


class ConversationState(Enum):
    """States of the conversation."""
    IDLE = "idle"
    LISTENING = "listening"
    PROCESSING = "processing"
    SPEAKING = "speaking"


@dataclass
class ConversationTurn:
    """Represents a single turn in the conversation."""
    role: str  # "user" or "assistant"
    text: str
    timestamp: datetime = field(default_factory=datetime.now)


class ConversationManager:
    """
    Manages the state and flow of a real-time conversation.
    Handles turn-taking, interruptions, and state transitions.
    """

    def __init__(self):
        self.state = ConversationState.IDLE
        self.history: List[ConversationTurn] = []
        self.current_transcript = ""
        self.is_interrupted = False
        self._state_callbacks: List[Callable[[ConversationState], None]] = []
        self._lock = asyncio.Lock()

    async def set_state(self, new_state: ConversationState):
        """Change conversation state and notify listeners."""
        async with self._lock:
            old_state = self.state
            self.state = new_state

            for callback in self._state_callbacks:
                try:
                    if asyncio.iscoroutinefunction(callback):
                        await callback(new_state)
                    else:
                        callback(new_state)
                except Exception:
                    pass

    def on_state_change(self, callback: Callable[[ConversationState], None]):
        """Register a callback for state changes."""
        self._state_callbacks.append(callback)

    async def start_listening(self):
        """Transition to listening state."""
        self.current_transcript = ""
        await self.set_state(ConversationState.LISTENING)

    async def update_transcript(self, text: str, is_final: bool = False):
        """Update the current transcript with new speech."""
        self.current_transcript = text

        if is_final and text.strip():
            self.history.append(ConversationTurn(role="user", text=text))
            await self.set_state(ConversationState.PROCESSING)

    async def start_speaking(self):
        """Transition to speaking state."""
        self.is_interrupted = False
        await self.set_state(ConversationState.SPEAKING)

    async def add_response(self, text: str):
        """Add assistant's response to history."""
        self.history.append(ConversationTurn(role="assistant", text=text))

    async def interrupt(self):
        """Handle user interruption during AI speech."""
        if self.state == ConversationState.SPEAKING:
            self.is_interrupted = True
            await self.set_state(ConversationState.LISTENING)
            return True
        return False

    async def finish_speaking(self):
        """Called when AI finishes speaking."""
        if not self.is_interrupted:
            await self.set_state(ConversationState.LISTENING)

    async def stop(self):
        """Stop the conversation."""
        await self.set_state(ConversationState.IDLE)
        self.current_transcript = ""

    def get_history_for_display(self) -> List[dict]:
        """Get conversation history formatted for display."""
        return [
            {
                "role": turn.role,
                "text": turn.text,
                "timestamp": turn.timestamp.isoformat(),
            }
            for turn in self.history
        ]

    def clear_history(self):
        """Clear conversation history."""
        self.history = []
        self.current_transcript = ""
