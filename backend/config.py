"""Centralized environment configuration."""
import os

from dotenv import load_dotenv

load_dotenv()

_REQUIRED_KEYS = ("SUPABASE_URL", "SUPABASE_KEY", "OPENAI_API_KEY")
_OPTIONAL_KEYS = (
    ("OPENAI_MODEL", "gpt-4o-mini"),
    ("OPENAI_TRANSCRIBE_MODEL", "whisper-1"),
    ("OPENAI_TTS_MODEL", "tts-1"),
    ("OPENAI_TTS_VOICE", "alloy"),
)


def _get_setting(name: str, default: str = "") -> str:
    """Read from environment variables, then Streamlit secrets (Cloud deploy)."""
    value = os.getenv(name)
    if value:
        return value

    try:
        import streamlit as st

        if name in st.secrets:
            return str(st.secrets[name])
    except Exception:
        pass

    return default


class Config:
    SUPABASE_URL: str = ""
    SUPABASE_KEY: str = ""
    OPENAI_API_KEY: str = ""
    OPENAI_MODEL: str = "gpt-4o-mini"
    OPENAI_TRANSCRIBE_MODEL: str = "whisper-1"
    OPENAI_TTS_MODEL: str = "tts-1"
    OPENAI_TTS_VOICE: str = "alloy"

    @classmethod
    def refresh(cls):
        cls.SUPABASE_URL = _get_setting("SUPABASE_URL")
        cls.SUPABASE_KEY = _get_setting("SUPABASE_KEY")
        cls.OPENAI_API_KEY = _get_setting("OPENAI_API_KEY")
        for name, default in _OPTIONAL_KEYS:
            setattr(cls, name, _get_setting(name, default))

    @classmethod
    def validate(cls):
        cls.refresh()
        missing = [name for name in _REQUIRED_KEYS if not getattr(cls, name)]
        if missing:
            raise RuntimeError(
                f"Missing required configuration: {', '.join(missing)}. "
                "For local dev, copy .env.example to .env and fill in your credentials. "
                "On Streamlit Cloud, add the same keys under App settings → Secrets."
            )


config = Config()
config.refresh()
