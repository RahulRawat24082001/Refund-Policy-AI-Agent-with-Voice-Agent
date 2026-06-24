"""Cached read helpers shared by streamlit_app.py and the admin dashboard."""
import streamlit as st

from backend.supabase_client import get_supabase


@st.cache_data(ttl=30)
def fetch_customers():
    sb = get_supabase()
    return sb.table("customers").select("*").order("customer_id").execute().data


@st.cache_data(ttl=30)
def fetch_orders():
    sb = get_supabase()
    return sb.table("orders").select("*").order("order_id").execute().data


@st.cache_data(ttl=10)
def fetch_refund_requests():
    sb = get_supabase()
    return (
        sb.table("refund_requests")
        .select("*")
        .order("created_at", desc=True)
        .execute()
        .data
    )
