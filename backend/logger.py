"""
Reasoning-log persistence. Every step of the agent loop (user message,
agent thoughts, tool calls, tool results, final response) is written here
so the admin dashboard can render a real-time trace per session.
"""
from backend.supabase_client import get_supabase

VALID_STEP_TYPES = {"user_message", "agent_thought", "tool_call", "tool_result", "final_response"}


def log_step(session_id: str, step_type: str, content: str, node_name: str = None):
    if step_type not in VALID_STEP_TYPES:
        raise ValueError(f"Invalid step_type '{step_type}'. Must be one of {VALID_STEP_TYPES}.")
    sb = get_supabase()
    sb.table("agent_logs").insert({
        "session_id": session_id,
        "node_name": node_name,
        "step_type": step_type,
        "content": content,
    }).execute()


def get_logs_for_session(session_id: str) -> list:
    sb = get_supabase()
    resp = (
        sb.table("agent_logs")
        .select("*")
        .eq("session_id", session_id)
        .order("created_at", desc=False)
        .execute()
    )
    return resp.data


def get_all_sessions() -> list:
    """Return distinct session_ids ordered by most recent activity."""
    sb = get_supabase()
    resp = (
        sb.table("agent_logs")
        .select("session_id, created_at")
        .order("created_at", desc=True)
        .limit(2000)
        .execute()
    )
    seen = []
    for row in resp.data:
        if row["session_id"] not in seen:
            seen.append(row["session_id"])
    return seen


def get_recent_logs(limit: int = 200) -> list:
    sb = get_supabase()
    resp = (
        sb.table("agent_logs")
        .select("*")
        .order("created_at", desc=True)
        .limit(limit)
        .execute()
    )
    return list(reversed(resp.data))
