"""
Tools the agent can call. Each tool is a thin, auditable wrapper around
Supabase lookups and the deterministic policy engine in policy_engine.py.
The LLM never computes eligibility or amounts itself — it only calls these
tools and narrates the results to the customer.
"""
import json
from datetime import date, timedelta

from langchain_core.tools import tool

from backend.policy_engine import (
    calculate_refund_amount as _calculate_refund_amount,
    check_frequent_returner,
    evaluate_eligibility,
)
from backend.supabase_client import get_supabase


def _row_or_none(resp):
    data = resp.data
    return data[0] if data else None


@tool
def lookup_customer(email: str) -> str:
    """Look up a customer's CRM profile by email address. Returns JSON with
    customer_id, name, loyalty_tier, account_flag, total_orders, etc.
    Use this first to verify the customer's identity before doing anything else.
    """
    sb = get_supabase()
    resp = sb.table("customers").select("*").eq("email", email.strip().lower()).execute()
    row = _row_or_none(resp)
    if not row:
        return json.dumps({"found": False, "error": f"No customer found with email '{email}'."})
    return json.dumps({"found": True, "customer": row})


@tool
def get_customer_orders(customer_id: str) -> str:
    """List all orders belonging to a given customer_id. Use this to help the
    customer find an order if they don't remember the exact order_id.
    """
    sb = get_supabase()
    resp = sb.table("orders").select("*").eq("customer_id", customer_id).execute()
    return json.dumps({"orders": resp.data})


@tool
def get_order_details(order_id: str) -> str:
    """Fetch full details for a single order_id (product, category, dates,
    amount, status). Use this to confirm the order exists before evaluating
    a refund.
    """
    sb = get_supabase()
    resp = sb.table("orders").select("*").eq("order_id", order_id).execute()
    row = _row_or_none(resp)
    if not row:
        return json.dumps({"found": False, "error": f"No order found with id '{order_id}'."})
    return json.dumps({"found": True, "order": row})


@tool
def check_refund_eligibility(order_id: str, customer_id: str, claimed_defective: bool) -> str:
    """
    Run the order against the refund policy rules engine. Set
    claimed_defective=True only if the customer says the item arrived
    defective, damaged, or wrong. Returns the eligibility window math,
    whether the order falls within it, and a recommended_decision of
    'approve', 'deny', or 'escalate' with an explanation citing the policy
    section. This does NOT check fraud/frequent-returner flags — call
    check_customer_risk_flags for that.
    """
    sb = get_supabase()
    order_resp = sb.table("orders").select("*").eq("order_id", order_id).execute()
    order = _row_or_none(order_resp)
    if not order:
        return json.dumps({"error": f"No order found with id '{order_id}'."})
    if order["customer_id"] != customer_id:
        return json.dumps({
            "error": "Order does not belong to this customer_id. Cannot verify proof of purchase (Policy Section 8).",
            "recommended_decision": "deny",
        })

    cust_resp = sb.table("customers").select("*").eq("customer_id", customer_id).execute()
    customer = _row_or_none(cust_resp)
    if not customer:
        return json.dumps({"error": f"No customer found with id '{customer_id}'."})

    result = evaluate_eligibility(order, customer, claimed_defective)
    result["order_id"] = order_id
    result["customer_id"] = customer_id
    return json.dumps(result)


@tool
def check_customer_risk_flags(customer_id: str) -> str:
    """
    Check whether this customer must be escalated to a human regardless of
    eligibility: fraud_watch account flag, or frequent_returner status
    (more than 5 approved refunds in the trailing 90 days). Always call
    this before finalizing an approve/deny decision (Policy Section 6).
    """
    sb = get_supabase()
    cust_resp = sb.table("customers").select("*").eq("customer_id", customer_id).execute()
    customer = _row_or_none(cust_resp)
    if not customer:
        return json.dumps({"error": f"No customer found with id '{customer_id}'."})

    cutoff = (date.today() - timedelta(days=90)).isoformat()
    hist_resp = (
        sb.table("refund_requests")
        .select("created_at")
        .eq("customer_id", customer_id)
        .eq("decision", "approved")
        .gte("created_at", cutoff)
        .execute()
    )
    approved_dates = [row["created_at"] for row in hist_resp.data]
    frequent = check_frequent_returner(customer_id, approved_dates)

    fraud_watch = customer.get("account_flag") == "fraud_watch"
    requires_escalation = fraud_watch or frequent["is_frequent_returner"]

    return json.dumps({
        "customer_id": customer_id,
        "fraud_watch": fraud_watch,
        **frequent,
        "requires_escalation": requires_escalation,
    })


@tool
def calculate_refund_amount(order_id: str, restocking_fee_pct: float, defective_override_applied: bool) -> str:
    """
    Calculate the exact refund amount for an order given the
    restocking_fee_pct and defective_override_applied values returned by
    check_refund_eligibility. Only call this after check_refund_eligibility
    has returned recommended_decision='approve'.
    """
    sb = get_supabase()
    order_resp = sb.table("orders").select("*").eq("order_id", order_id).execute()
    order = _row_or_none(order_resp)
    if not order:
        return json.dumps({"error": f"No order found with id '{order_id}'."})

    fake_eligibility = {
        "restocking_fee_pct": restocking_fee_pct,
        "defective_override_applied": defective_override_applied,
    }
    result = _calculate_refund_amount(order, fake_eligibility)
    result["order_id"] = order_id
    return json.dumps(result)


@tool
def log_refund_decision(
    order_id: str,
    customer_id: str,
    reason: str,
    claimed_defective: bool,
    decision: str,
    refund_amount: float,
    explanation: str,
) -> str:
    """
    Record the final decision (approved / denied / escalated) to the audit
    trail. ALWAYS call this exactly once at the end of every refund
    request, regardless of the outcome, including escalations (use
    refund_amount=0 for denials/escalations).
    """
    if decision not in ("approved", "denied", "escalated"):
        return json.dumps({"error": "decision must be one of approved/denied/escalated"})
    sb = get_supabase()
    row = {
        "order_id": order_id,
        "customer_id": customer_id,
        "reason": reason,
        "claimed_defective": claimed_defective,
        "decision": decision,
        "refund_amount": refund_amount,
        "explanation": explanation,
    }
    sb.table("refund_requests").insert(row).execute()
    return json.dumps({"logged": True, **row})


ALL_TOOLS = [
    lookup_customer,
    get_customer_orders,
    get_order_details,
    check_refund_eligibility,
    check_customer_risk_flags,
    calculate_refund_amount,
    log_refund_decision,
]
