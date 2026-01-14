from google.cloud import texttospeech
from app.config import TTS_LANGUAGE_CODE


class TextToSpeech:
    """Handles text-to-speech using Google Cloud Text-to-Speech API."""

    def __init__(self):
        self.client = texttospeech.TextToSpeechClient()

    def synthesize(
        self,
        text: str,
        voice_name: str = "en-US-Neural2-D",
        speaking_rate: float = 1.0,
        pitch: float = 0.0,
    ) -> bytes:
        """
        Convert text to speech audio.

        Args:
            text: The text to convert to speech
            voice_name: Google TTS voice name (e.g., "en-US-Neural2-D")
            speaking_rate: Speed of speech (0.25 to 4.0, default 1.0)
            pitch: Voice pitch (-20.0 to 20.0, default 0.0)

        Returns:
            Audio content as bytes (MP3 format)
        """
        synthesis_input = texttospeech.SynthesisInput(text=text)

        # Extract language code from voice name (e.g., "en-US" from "en-US-Neural2-D")
        language_code = "-".join(voice_name.split("-")[:2])

        voice = texttospeech.VoiceSelectionParams(
            language_code=language_code,
            name=voice_name,
        )

        audio_config = texttospeech.AudioConfig(
            audio_encoding=texttospeech.AudioEncoding.MP3,
            speaking_rate=speaking_rate,
            pitch=pitch,
        )

        response = self.client.synthesize_speech(
            input=synthesis_input,
            voice=voice,
            audio_config=audio_config,
        )

        return response.audio_content

    def synthesize_ssml(
        self,
        ssml: str,
        voice_name: str = "en-US-Neural2-D",
        speaking_rate: float = 1.0,
        pitch: float = 0.0,
    ) -> bytes:
        """
        Convert SSML to speech audio for more control over pronunciation.

        Args:
            ssml: SSML-formatted text
            voice_name: Google TTS voice name
            speaking_rate: Speed of speech
            pitch: Voice pitch

        Returns:
            Audio content as bytes (MP3 format)
        """
        synthesis_input = texttospeech.SynthesisInput(ssml=ssml)

        language_code = "-".join(voice_name.split("-")[:2])

        voice = texttospeech.VoiceSelectionParams(
            language_code=language_code,
            name=voice_name,
        )

        audio_config = texttospeech.AudioConfig(
            audio_encoding=texttospeech.AudioEncoding.MP3,
            speaking_rate=speaking_rate,
            pitch=pitch,
        )

        response = self.client.synthesize_speech(
            input=synthesis_input,
            voice=voice,
            audio_config=audio_config,
        )

        return response.audio_content

    @staticmethod
    def list_voices(language_code: str = "en-US") -> list:
        """
        List available voices for a language.

        Returns:
            List of voice names
        """
        client = texttospeech.TextToSpeechClient()
        response = client.list_voices(language_code=language_code)

        voices = []
        for voice in response.voices:
            voices.append({
                "name": voice.name,
                "gender": texttospeech.SsmlVoiceGender(voice.ssml_gender).name,
                "natural_sample_rate": voice.natural_sample_rate_hertz,
            })

        return voices


# Pre-configured voice options for characters
VOICE_PRESETS = {
    "wizard": {
        "voice_name": "en-US-Neural2-D",  # Deep male voice
        "speaking_rate": 0.9,
        "pitch": -2.0,
    },
    "interviewer": {
        "voice_name": "en-US-Neural2-F",  # Professional female voice
        "speaking_rate": 1.0,
        "pitch": 0.0,
    },
    "tutor": {
        "voice_name": "en-US-Neural2-C",  # Friendly female voice
        "speaking_rate": 0.95,
        "pitch": 1.0,
    },
    "default": {
        "voice_name": "en-US-Neural2-A",
        "speaking_rate": 1.0,
        "pitch": 0.0,
    },
}
