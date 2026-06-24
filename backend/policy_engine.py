"""
Deterministic refund-policy rules engine.

This module is the programmatic source of truth that mirrors
`data/refund_policy.md`. The LLM agent never decides eligibility math
itself — it calls the tools in `backend/tools.py`, which call into this
engine, so every decision is auditable and reproducible.
"""
from datetime import date, datetime
from typing import Optional

# ---- Section 1: category windows -----------------------------------------
CATEGORY_RULES = {
    "electronics": {"window_days": 15, "restocking_fee_pct": 0},
    "apparel":     {"window_days": 30, "restocking_fee_pct": 0},
    "beauty":      {"window_days": 7,  "restocking_fee_pct": 0},
    "furniture":   {"window_days": 30, "restocking_fee_pct": 15},
    "books":       {"window_days": 30, "restocking_fee_pct": 0},
    "grocery":     {"window_days": 0,  "restocking_fee_pct": 0},
    "final_sale":  {"window_days": 0,  "restocking_fee_pct": 0},
}

# ---- Section 3: loyalty grace ---------------------------------------------
LOYALTY_GRACE_DAYS = {"standard": 0, "silver": 5, "gold": 10, "platinum": 15}
LOYALTY_WAIVES_RESTOCKING = {"standard": False, "silver": False, "gold": True, "platinum": True}

# ---- Section 2 / 6 ----------------------------------------------------------
DEFECTIVE_WINDOW_DAYS = 90
FREQUENT_RETURNER_THRESHOLD = 5  # more than this many approvals in 90 days -> escalate
FREQUENT_RETURNER_LOOKBACK_DAYS = 90


def _parse_date(value) -> Optional[date]:
    if value is None:
        return None
    if isinstance(value, date):
        return value
    return datetime.fromisoformat(str(value)).date()


def evaluate_eligibility(order: dict, customer: dict, claimed_defective: bool, today: Optional[date] = None) -> dict:
    """
    Pure rules-engine evaluation of a single refund request.

    Returns a dict describing every intermediate fact the policy cares
    about, plus a `recommended_decision` of "approve" | "deny" | "escalate"
    and a human-readable `explanation`.
    """
    today = today or date.today()
    notes = []

    category = order.get("category")
    status = order.get("status")
    loyalty_tier = customer.get("loyalty_tier", "standard")
    account_flag = customer.get("account_flag", "none")

    # --- Section 6: hard escalation flags, checked first -------------------
    if account_flag == "fraud_watch":
        return {
            "recommended_decision": "escalate",
            "reason_code": "fraud_watch_flag",
            "explanation": "Customer account is flagged fraud_watch. Policy Section 6 requires escalation to a human agent regardless of eligibility math.",
            "notes": notes,
        }

    # --- Section 5: order status -------------------------------------------
    if status == "refunded":
        return {
            "recommended_decision": "deny",
            "reason_code": "already_refunded",
            "explanation": "This order has already been refunded. Policy Section 5 prohibits refunding the same order twice.",
            "notes": notes,
        }

    if status != "delivered":
        return {
            "recommended_decision": "escalate",
            "reason_code": "non_delivered_status",
            "explanation": f"Order status is '{status}', not 'delivered'. Policy Section 5 requires escalation for cancelled/in-transit orders — this agent does not handle them.",
            "notes": notes,
        }

    if category not in CATEGORY_RULES:
        return {
            "recommended_decision": "escalate",
            "reason_code": "unknown_category",
            "explanation": f"Category '{category}' is not covered by this policy. Escalating per Section 9.",
            "notes": notes,
        }

    delivery_date = _parse_date(order.get("delivery_date"))
    if delivery_date is None:
        return {
            "recommended_decision": "escalate",
            "reason_code": "missing_delivery_date",
            "explanation": "Order has no delivery date on file; cannot compute eligibility window. Escalating for manual review.",
            "notes": notes,
        }

    days_since_delivery = (today - delivery_date).days

    # --- Section 1: categories with a 0-day standard window (final_sale,
    # grocery) have no return right for non-defective items, and loyalty
    # grace does not create one out of thin air. final_sale is further an
    # absolute bar even when the item is claimed defective.
    if category == "final_sale":
        return {
            "recommended_decision": "deny",
            "reason_code": "final_sale_no_refunds",
            "explanation": "Item is marked final_sale / clearance. Policy Section 1 states these items are never refundable, with no exceptions.",
            "days_since_delivery": days_since_delivery,
            "notes": notes,
        }

    rule = CATEGORY_RULES[category]
    base_window = rule["window_days"]
    restocking_fee_pct = rule["restocking_fee_pct"]
    grace_days = LOYALTY_GRACE_DAYS.get(loyalty_tier, 0) if base_window > 0 else 0

    defective_override_applied = False
    if claimed_defective:
        # --- Section 2: defective/damaged override --------------------------
        effective_window = DEFECTIVE_WINDOW_DAYS
        restocking_fee_pct = 0
        defective_override_applied = True
        notes.append("Defective/damaged-on-arrival override applied (Section 2): window=90 days, restocking fee waived, shipping refundable.")
    else:
        effective_window = base_window + grace_days
        if LOYALTY_WAIVES_RESTOCKING.get(loyalty_tier, False):
            restocking_fee_pct = 0
            if rule["restocking_fee_pct"] > 0:
                notes.append(f"Restocking fee waived due to {loyalty_tier} loyalty tier (Section 3).")
        if grace_days:
            notes.append(f"{loyalty_tier.title()} tier grants +{grace_days} grace days (Section 3): {base_window} + {grace_days} = {effective_window} days.")

    within_window = days_since_delivery <= effective_window

    result = {
        "category": category,
        "days_since_delivery": days_since_delivery,
        "base_window_days": base_window,
        "loyalty_tier": loyalty_tier,
        "grace_days": grace_days,
        "effective_window_days": effective_window,
        "within_window": within_window,
        "defective_override_applied": defective_override_applied,
        "restocking_fee_pct": restocking_fee_pct,
        "notes": notes,
    }

    if within_window:
        result["recommended_decision"] = "approve"
        result["reason_code"] = "within_window"
        result["explanation"] = (
            f"Order delivered {days_since_delivery} days ago; eligible window for "
            f"category '{category}' is {effective_window} days"
            f"{' (defective override)' if defective_override_applied else ''}. Eligible for refund."
        )
    else:
        result["recommended_decision"] = "deny"
        result["reason_code"] = "window_expired"
        result["explanation"] = (
            f"Order delivered {days_since_delivery} days ago, which exceeds the "
            f"{effective_window}-day eligible window for category '{category}'. Not eligible."
        )

    return result


def check_frequent_returner(customer_id: str, approved_refund_dates: list, today: Optional[date] = None) -> dict:
    """
    Section 6: flag a customer as a frequent_returner if they have more
    than FREQUENT_RETURNER_THRESHOLD approved refunds in the trailing
    FREQUENT_RETURNER_LOOKBACK_DAYS days.

    `approved_refund_dates` is a list of ISO date/datetime strings of
    previously *approved* refund_requests for this customer.
    """
    today = today or date.today()
    cutoff = today.toordinal() - FREQUENT_RETURNER_LOOKBACK_DAYS
    recent_count = 0
    for raw in approved_refund_dates:
        try:
            dt = datetime.fromisoformat(str(raw).replace("Z", "+00:00")).date()
        except ValueError:
            continue
        if dt.toordinal() >= cutoff:
            recent_count += 1

    is_frequent = recent_count > FREQUENT_RETURNER_THRESHOLD
    return {
        "customer_id": customer_id,
        "approved_refunds_last_90_days": recent_count,
        "is_frequent_returner": is_frequent,
        "explanation": (
            f"{recent_count} approved refunds in the trailing {FREQUENT_RETURNER_LOOKBACK_DAYS} days "
            f"{'exceeds' if is_frequent else 'does not exceed'} the threshold of "
            f"{FREQUENT_RETURNER_THRESHOLD} (Section 6)."
        ),
    }


def calculate_refund_amount(order: dict, eligibility: dict) -> dict:
    """Section 7: compute the actual refund amount given an eligibility result."""
    amount = float(order.get("amount", 0))
    shipping = float(order.get("shipping_amount", 0))
    restocking_pct = eligibility.get("restocking_fee_pct", 0)
    defective = eligibility.get("defective_override_applied", False)

    restocking_fee_amount = round(amount * (restocking_pct / 100), 2)
    shipping_refunded = defective  # Section 7: shipping refunded only if defective/damaged/wrong item
    total = round(amount - restocking_fee_amount + (shipping if shipping_refunded else 0), 2)

    return {
        "base_amount": amount,
        "restocking_fee_pct": restocking_pct,
        "restocking_fee_amount": restocking_fee_amount,
        "shipping_amount": shipping,
        "shipping_refunded": shipping_refunded,
        "total_refund": max(total, 0.0),
    }
