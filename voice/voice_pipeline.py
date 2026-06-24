"""
Minimal voice pipeline for the bonus mic-in / speech-out flow.

Uses OpenAI directly so it shares the same API key/billing as the agent's
LLM, with no extra third-party account needed to demo voice:

- Speech-to-text: OpenAI Whisper (`whisper-1`)
- Text-to-speech: OpenAI TTS (`tts-1`, configurable voice)

Swap-friendly: replace `transcribe_audio` / `synthesize_speech` with
ElevenLabs / LiveKit / the OpenAI Realtime API calls if you want lower
latency or full duplex streaming — the rest of the app (agent_graph,
Streamlit UI) doesn't need to change.
"""
import io

from openai import OpenAI

from backend.config import config

_client = None


def _get_client() -> OpenAI:
    global _client
    if _client is None:
        _client = OpenAI(api_key=config.OPENAI_API_KEY)
    return _client


def transcribe_audio(audio_bytes: bytes, filename: str = "input.wav") -> str:
    """Transcribe raw audio bytes (wav/mp3/webm) to text via Whisper."""
    client = _get_client()
    audio_file = io.BytesIO(audio_bytes)
    audio_file.name = filename  # the SDK reads this to infer the format
    transcript = client.audio.transcriptions.create(
        model=config.OPENAI_TRANSCRIBE_MODEL,
        file=audio_file,
    )
    return transcript.text.strip()


def synthesize_speech(text: str) -> bytes:
    """Convert text to spoken audio (mp3 bytes) via OpenAI TTS."""
    client = _get_client()
    response = client.audio.speech.create(
        model=config.OPENAI_TTS_MODEL,
        voice=config.OPENAI_TTS_VOICE,
        input=text,
    )
    return response.read()
