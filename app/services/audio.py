# ElevenLabs audio generation service
import os
import base64
from elevenlabs import ElevenLabs
from dotenv import load_dotenv
class AudioService:
    def __init__(self):
        load_dotenv()
        api_key = os.getenv("ELEVENLABS_API_KEY")
        self.eleven_client = ElevenLabs(api_key=api_key)
        self.voice_id = "xg7RXypgOlRSIidsSV4l"
        self.model_id = "eleven_flash_v2_5"

    def generate_audio(self, text: str) -> str:
        audio = self.eleven_client.text_to_speech.convert(
            voice_id=self.voice_id,
            text=text,
            model_id=self.model_id
        )
        audio_bytes = b"".join(audio)
        audio_base64 = base64.b64encode(audio_bytes).decode("utf-8")
        return audio_base64
