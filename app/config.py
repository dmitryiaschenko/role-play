import os
from dotenv import load_dotenv

load_dotenv()

# Google Cloud credentials
GOOGLE_APPLICATION_CREDENTIALS = os.getenv("GOOGLE_APPLICATION_CREDENTIALS")
GOOGLE_API_KEY = os.getenv("GOOGLE_API_KEY")
GOOGLE_CLOUD_PROJECT = os.getenv("GOOGLE_CLOUD_PROJECT")

# Audio settings
SAMPLE_RATE = 16000  # Hz - Google Speech-to-Text works best with 16kHz
CHANNELS = 1  # Mono audio
CHUNK_SIZE = 4096  # Bytes per audio chunk

# Speech-to-Text settings
STT_LANGUAGE_CODE = "en-US"
STT_MODEL = "latest_long"  # Good for conversations

# Text-to-Speech settings
TTS_LANGUAGE_CODE = "en-US"
TTS_AUDIO_ENCODING = "MP3"
