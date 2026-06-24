"""
Admin Dashboard — real-time agent reasoning logs, refund decision audit
trail, and CRM browser.

Streamlit auto-discovers this as a second page because it lives in
pages/ next to the root streamlit_app.py.
"""
import json

import pandas as pd
import streamlit as st
from streamlit_autorefresh import st_autorefresh

from backend.config import config
from backend.logger import get_all_sessions, get_logs_for_session, get_recent_logs
from utils.data_helpers import fetch_customers, fetch_orders, fetch_refund_requests

st.set_page_config(page_title="Admin Dashboard", page_icon="🛠️", layout="wide")

STEP_ICONS = {
    "user_message": "🗣️",
    "agent_thought": "🤔",
    "tool_call": "🔧",
    "tool_result": "📦",
    "final_response": "✅",
}

DECISION_COLORS = {"approved": "🟢", "denied": "🔴", "escalated": "🟡"}


def render_log_entry(entry: dict):
    icon = STEP_ICONS.get(entry["step_type"], "•")
    ts = entry.get("created_at", "")[11:19] if entry.get("created_at") else ""
    label = entry["step_type"].replace("_", " ").title()

    with st.container(border=True):
        st.markdown(f"{icon} **{label}**  ·  `{ts}`  ·  node: `{entry.get('node_name') or '—'}`")
        content = entry.get("content") or ""
        try:
            parsed = json.loads(content)
            st.json(parsed, expanded=False)
        except (json.JSONDecodeError, TypeError):
            st.markdown(content)


def main():
    try:
        config.validate()
    except RuntimeError as exc:
        st.error(str(exc))
        st.stop()

    st.title("🛠️ Admin Dashboard")
    st.caption("Real-time agent reasoning logs, refund decisions, and CRM data.")

    with st.sidebar:
        st.header("Controls")
        auto_refresh = st.toggle("🔁 Auto-refresh", value=True)
        interval_s = st.slider("Refresh interval (seconds)", 2, 30, 4)
        if auto_refresh:
            st_autorefresh(interval=interval_s * 1000, key="admin_autorefresh")
        if st.button("Refresh now", use_container_width=True):
            st.cache_data.clear()
            st.rerun()

    tab_trace, tab_decisions, tab_crm = st.tabs(
        ["🧠 Live Reasoning Trace", "📋 Refund Decisions", "👥 CRM Browser"]
    )

    # ---------------------------------------------------------------- TRACE
    with tab_trace:
        sessions = get_all_sessions()
        col_a, col_b = st.columns([2, 1])
        with col_a:
            if sessions:
                selected_session = st.selectbox(
                    "Conversation session", sessions, index=0,
                    format_func=lambda s: f"Session {s}",
                )
            else:
                selected_session = None
                st.info("No conversations yet. Chat with the agent in the main app to generate logs.")
        with col_b:
            show_global_feed = st.toggle("Show global activity feed instead", value=False)

        st.divider()

        if show_global_feed:
            st.subheader("Global activity feed (most recent across all sessions)")
            logs = get_recent_logs(limit=100)
            for entry in reversed(logs):
                render_log_entry(entry)
        elif selected_session:
            st.subheader(f"Reasoning trace — session `{selected_session}`")
            logs = get_logs_for_session(selected_session)
            if not logs:
                st.info("No steps logged yet for this session.")
            for entry in logs:
                render_log_entry(entry)

    # ------------------------------------------------------------ DECISIONS
    with tab_decisions:
        st.subheader("Refund decision audit trail")
        requests = fetch_refund_requests()

        if not requests:
            st.info("No refund decisions logged yet.")
        else:
            df = pd.DataFrame(requests)

            c1, c2, c3, c4 = st.columns(4)
            c1.metric("Total requests", len(df))
            c2.metric("Approved", int((df["decision"] == "approved").sum()))
            c3.metric("Denied", int((df["decision"] == "denied").sum()))
            c4.metric("Escalated", int((df["decision"] == "escalated").sum()))

            total_refunded = df.loc[df["decision"] == "approved", "refund_amount"].astype(float).sum()
            st.metric("💰 Total refunded", f"${total_refunded:,.2f}")

            decision_filter = st.multiselect(
                "Filter by decision", options=["approved", "denied", "escalated"],
                default=["approved", "denied", "escalated"],
            )
            filtered = df[df["decision"].isin(decision_filter)]

            display_df = filtered.copy()
            display_df["decision"] = display_df["decision"].map(lambda d: f"{DECISION_COLORS.get(d, '')} {d}")
            st.dataframe(
                display_df[[
                    "created_at", "order_id", "customer_id", "decision",
                    "refund_amount", "claimed_defective", "reason", "explanation",
                ]],
                use_container_width=True,
                hide_index=True,
            )

    # ------------------------------------------------------------------ CRM
    with tab_crm:
        st.subheader("Customers (15 seeded CRM profiles)")
        customers = fetch_customers()
        st.dataframe(pd.DataFrame(customers), use_container_width=True, hide_index=True)

        st.subheader("Orders")
        orders = fetch_orders()
        st.dataframe(pd.DataFrame(orders), use_container_width=True, hide_index=True)


if __name__ == "__main__":
    main()
