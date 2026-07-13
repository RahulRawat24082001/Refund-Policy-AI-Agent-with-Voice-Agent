"""Singleton Supabase client used across the backend."""
from functools import lru_cache

from supabase import Client, create_client

from backend.config import config


@lru_cache(maxsize=1)
def get_supabase() -> Client:
    config.refresh()
    if not config.SUPABASE_URL or not config.SUPABASE_KEY:
        raise RuntimeError(
            "SUPABASE_URL / SUPABASE_KEY are not set. For local dev, copy "
            ".env.example to .env. On Streamlit Cloud, add them under "
            "App settings → Secrets."
        )
    return create_client(config.SUPABASE_URL, config.SUPABASE_KEY)
