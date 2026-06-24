"""Singleton Supabase client used across the backend."""
from functools import lru_cache

from supabase import Client, create_client

from backend.config import config


@lru_cache(maxsize=1)
def get_supabase() -> Client:
    if not config.SUPABASE_URL or not config.SUPABASE_KEY:
        raise RuntimeError(
            "SUPABASE_URL / SUPABASE_KEY are not set. Copy .env.example to .env "
            "and fill in your Supabase project credentials."
        )
    return create_client(config.SUPABASE_URL, config.SUPABASE_KEY)
