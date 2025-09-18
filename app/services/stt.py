# # app/services/stt.py
# import io
# import numpy as np
# import subprocess
# from faster_whisper import WhisperModel


# class STTService:
#     def __init__(self):
#         # Load Whisper once at startup
#         print("[stt] Loading Whisper model...")
#         self.model = WhisperModel("base", device="cpu", compute_type="int8")
#         print("[stt] Whisper model loaded")

#     def decode_opus_webm(self, data: bytes) -> np.ndarray:
#         """Decode webm/opus bytes to float32 PCM using ffmpeg"""
#         process = subprocess.Popen(
#             [
#                 "ffmpeg",
#                 "-i", "pipe:0",        # input from stdin
#                 "-f", "f32le",         # raw 32-bit float
#                 "-ar", "16000",        # resample to 16kHz (Whisper requirement)
#                 "-ac", "1",            # mono
#                 "pipe:1"               # output to stdout
#             ],
#             stdin=subprocess.PIPE,
#             stdout=subprocess.PIPE,
#             stderr=subprocess.DEVNULL
#         )
#         out, _ = process.communicate(input=data)
#         audio = np.frombuffer(out, np.float32)
#         return audio

#     async def transcribe_audio(self, websocket):
#         await websocket.accept()
#         print("[stt] WebSocket connection established")

#         audio_buffer = bytearray()
#         chunk_count = 0

#         try:
#             while True:
#                 # Receive audio chunk from frontend
#                 data = await websocket.receive_bytes()
#                 chunk_count += 1
#                 print(f"[stt] Received chunk {chunk_count}, size={len(data)} bytes")

#                 audio_buffer.extend(data)

#                 try:
#                     # Decode using ffmpeg
#                     audio = self.decode_opus_webm(audio_buffer)
#                     print(f"[stt] Decoded {len(audio)} samples")

#                     if len(audio) < 16000:  # less than 1s of audio
#                         print("[stt] Not enough audio yet, waiting for more...")
#                         continue

#                     # Transcribe with Whisper
#                     segments, _ = self.model.transcribe(audio, vad_filter=True)
#                     transcript = " ".join([seg.text for seg in segments]).strip()
#                     print(f"[stt] Transcript so far: {transcript}")

#                     if transcript:
#                         await websocket.send_text(transcript)
#                         print("[stt] Sent transcript to frontend")

#                 except Exception as e:
#                     print(f"[stt] Decode/transcribe error: {e}")
#                     continue

#         except Exception as e:
#             print(f"[stt] WebSocket error: {e}")
#             try:
#                 await websocket.close()
#             except Exception:
#                 pass


import io
import numpy as np
import subprocess
import asyncio
from faster_whisper import WhisperModel


class STTService:
    def __init__(self):
        print("[stt] Loading Whisper model...")
        self.model = WhisperModel("base", device="cpu", compute_type="int8")
        print("[stt] Whisper model loaded")

    async def decode_opus_webm(self, data: bytes) -> np.ndarray:
        """Async decode webm/opus bytes to float32 PCM using ffmpeg"""
        loop = asyncio.get_running_loop()
        return await loop.run_in_executor(None, self._decode_blocking, data)

    def _decode_blocking(self, data: bytes) -> np.ndarray:
        """Blocking ffmpeg decode (called in thread)"""
        process = subprocess.Popen(
            [
                "ffmpeg",
                "-i", "pipe:0",
                "-f", "f32le",
                "-ar", "16000",
                "-ac", "1",
                "pipe:1"
            ],
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=subprocess.DEVNULL
        )
        out, _ = process.communicate(input=data)
        audio = np.frombuffer(out, np.float32)
        return audio

    async def transcribe_audio(self, websocket):
        await websocket.accept()
        print("[stt] WebSocket connection established")

        # Keep a sliding buffer for context (~3 seconds)
        sliding_buffer = bytearray()
        CHUNK_SIZE = 16000 * 4  # 1 second of float32 audio
        MAX_BUFFER = CHUNK_SIZE * 3  # keep last 3 seconds

        chunk_count = 0

        try:
            while True:
                try:
                    data = await websocket.receive_bytes()
                except Exception as e:
                    print(f"[stt] WebSocket closed or error: {e}")
                    break

                chunk_count += 1
                print(f"[stt] Received chunk {chunk_count}, size={len(data)} bytes")

                # Add new chunk to sliding buffer
                sliding_buffer.extend(data)

                # Keep only the last MAX_BUFFER bytes
                if len(sliding_buffer) > MAX_BUFFER:
                    sliding_buffer = sliding_buffer[-MAX_BUFFER:]

                # Decode new data
                try:
                    audio = await self.decode_opus_webm(sliding_buffer)
                    print(f"[stt] Decoded {len(audio)} samples")

                    if len(audio) >= 16000:  # at least 1 second
                        # Transcribe using Whisper
                        segments, _ = self.model.transcribe(audio, vad_filter=True)
                        transcript = " ".join([seg.text for seg in segments]).strip()

                        if transcript:
                            await websocket.send_text(transcript)
                            print(f"[stt] Sent transcript: {transcript}")

                except Exception as e:
                    print(f"[stt] Decode/transcribe error: {e}")

        finally:
            try:
                if websocket.client_state.value != "DISCONNECTED":
                    await websocket.close()
                    print("[stt] WebSocket closed gracefully")
            except Exception as e:
                print(f"[stt] Error closing websocket: {e}")
