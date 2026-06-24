"""
Customer-facing Streamlit app: text chat + optional voice input/output,
backed by the LangGraph refund agent.

Run with:  streamlit run streamlit_app.py
"""
import uuid

import streamlit as st
from audio_recorder_streamlit import audio_recorder

from backend.agent_graph import build_agent_graph, run_agent_turn
from backend.config import config
from utils.data_helpers import fetch_customers, fetch_orders
from voice.voice_pipeline import synthesize_speech, transcribe_audio

st.set_page_config(page_title="Support Assistant", page_icon="🛟", layout="centered")

DEMO_EMAILS = [
    "ava.thompson@example.com", "liam.carter@example.com", "sophia.nguyen@example.com",
    "noah.patel@example.com", "mia.rodriguez@example.com", "ethan.walker@example.com",
    "isabella.kim@example.com", "lucas.martin@example.com", "charlotte.davis@example.com",
    "james.wilson@example.com", "amelia.garcia@example.com", "benjamin.lee@example.com",
    "harper.brown@example.com", "henry.clark@example.com", "evelyn.lewis@example.com",
]


@st.cache_resource(show_spinner=False)
def get_graph():
    return build_agent_graph()


def init_state():
    if "session_id" not in st.session_state:
        st.session_state.session_id = uuid.uuid4().hex[:12]
    if "messages" not in st.session_state:
        st.session_state.messages = []
    if "voice_replies" not in st.session_state:
        st.session_state.voice_replies = False
    if "last_audio_hash" not in st.session_state:
        st.session_state.last_audio_hash = None


def reset_conversation():
    st.session_state.session_id = uuid.uuid4().hex[:12]
    st.session_state.messages = []
    st.session_state.last_audio_hash = None


def handle_user_turn(user_text: str, prefix: str = ""):
    display_text = f"{prefix}{user_text}" if prefix else user_text
    st.session_state.messages.append({"role": "user", "content": display_text})
    with st.chat_message("user"):
        st.markdown(display_text)

    graph = get_graph()
    with st.chat_message("assistant"):
        with st.spinner("Looking into this..."):
            try:
                reply = run_agent_turn(graph, st.session_state.session_id, user_text)
            except Exception as exc:  # noqa: BLE001
                reply = (
                    "Sorry, I hit an error talking to the backend. "
                    f"Details: `{exc}`"
                )
        st.markdown(reply)

        audio_bytes = None
        if st.session_state.voice_replies and reply:
            with st.spinner("Generating voice reply..."):
                try:
                    audio_bytes = synthesize_speech(reply)
                except Exception:  # noqa: BLE001
                    audio_bytes = None
            if audio_bytes:
                st.audio(audio_bytes, format="audio/mp3")

    st.session_state.messages.append({"role": "assistant", "content": reply})


def main():
    init_state()

    try:
        config.validate()
    except RuntimeError as exc:
        st.error(str(exc))
        st.stop()

    with st.sidebar:
        st.header("🛟 Support Assistant")
        st.caption(f"Session ID: `{st.session_state.session_id}`")
        st.caption("Use this ID to find this conversation in the Admin Dashboard.")

        if st.button("🔄 New conversation", use_container_width=True):
            reset_conversation()
            st.rerun()

        st.divider()
        st.subheader("🎤 Voice")
        st.session_state.voice_replies = st.toggle(
            "Speak replies aloud", value=st.session_state.voice_replies
        )
        st.caption("Record a voice message instead of typing:")
        audio_bytes_in = audio_recorder(
            text="Click to record",
            recording_color="#e74c3c",
            neutral_color="#6c757d",
            icon_size="2x",
            key="mic_recorder",
        )

        st.divider()
        st.subheader("🧪 Demo data")
        st.caption("Seeded CRM emails you can use to test the agent:")
        with st.expander("Sample customers"):
            try:
                customers = fetch_customers()
                for c in customers:
                    st.write(f"**{c['name']}** — {c['email']} — {c['loyalty_tier']}")
            except Exception:  # noqa: BLE001
                for e in DEMO_EMAILS:
                    st.write(e)
        with st.expander("Sample orders"):
            try:
                orders = fetch_orders()
                for o in orders:
                    st.write(f"`{o['order_id']}` — {o['product_name']} ({o['category']}) — {o['status']}")
            except Exception:  # noqa: BLE001
                st.caption("Connect Supabase to browse seeded orders here.")

    st.title("Customer Support")
    st.caption(
        "Ask about a refund — I'll verify your account and order, then approve, "
        "deny, or escalate strictly according to policy."
    )

    if not st.session_state.messages:
        with st.chat_message("assistant"):
            st.markdown(
                "Hi! I'm your refund support assistant. To get started, could you "
                "share the email address on your account?"
            )

    for msg in st.session_state.messages:
        with st.chat_message(msg["role"]):
            st.markdown(msg["content"])

    # --- voice input ---------------------------------------------------------
    if audio_bytes_in:
        audio_hash = hash(audio_bytes_in)
        if audio_hash != st.session_state.last_audio_hash:
            st.session_state.last_audio_hash = audio_hash
            with st.spinner("Transcribing your voice message..."):
                try:
                    transcribed = transcribe_audio(audio_bytes_in, filename="input.wav")
                except Exception as exc:  # noqa: BLE001
                    transcribed = None
                    st.error(f"Couldn't transcribe audio: {exc}")
            if transcribed:
                handle_user_turn(transcribed, prefix="🎤 ")
                st.rerun()

    # --- text input ------------------------------------------------------------
    user_text = st.chat_input("Type your message...")
    if user_text:
        handle_user_turn(user_text)
        st.rerun()


if __name__ == "__main__":
    main()
