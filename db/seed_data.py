"""
Seed Supabase with 15 mock CRM customer profiles and a set of orders that
deliberately exercise every branch of the refund policy (data/refund_policy.md):
expired windows, loyalty grace extensions, defective overrides, final-sale
denials, fraud/frequent-returner escalations, already-refunded orders, and
non-delivered orders.

Run once:
    python db/seed_data.py
"""
import os
import sys
from datetime import date, timedelta

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from backend.supabase_client import get_supabase  # noqa: E402

TODAY = date.today()


def d(days_ago: int) -> str:
    """Return an ISO date string `days_ago` days before today."""
    return (TODAY - timedelta(days=days_ago)).isoformat()


CUSTOMERS = [
    {"customer_id": "CUST001", "name": "Ava Thompson",      "email": "ava.thompson@example.com",    "phone": "555-0101", "signup_date": d(800), "loyalty_tier": "standard", "total_orders": 3,  "account_flag": "none"},
    {"customer_id": "CUST002", "name": "Liam Carter",       "email": "liam.carter@example.com",     "phone": "555-0102", "signup_date": d(650), "loyalty_tier": "silver",   "total_orders": 7,  "account_flag": "none"},
    {"customer_id": "CUST003", "name": "Sophia Nguyen",     "email": "sophia.nguyen@example.com",   "phone": "555-0103", "signup_date": d(900), "loyalty_tier": "gold",     "total_orders": 14, "account_flag": "none"},
    {"customer_id": "CUST004", "name": "Noah Patel",        "email": "noah.patel@example.com",      "phone": "555-0104", "signup_date": d(1200),"loyalty_tier": "platinum", "total_orders": 26, "account_flag": "none"},
    {"customer_id": "CUST005", "name": "Mia Rodriguez",     "email": "mia.rodriguez@example.com",   "phone": "555-0105", "signup_date": d(300), "loyalty_tier": "standard", "total_orders": 4,  "account_flag": "fraud_watch"},
    {"customer_id": "CUST006", "name": "Ethan Walker",      "email": "ethan.walker@example.com",    "phone": "555-0106", "signup_date": d(420), "loyalty_tier": "silver",   "total_orders": 9,  "account_flag": "none"},
    {"customer_id": "CUST007", "name": "Isabella Kim",      "email": "isabella.kim@example.com",    "phone": "555-0107", "signup_date": d(540), "loyalty_tier": "gold",     "total_orders": 11, "account_flag": "none"},
    {"customer_id": "CUST008", "name": "Lucas Martin",      "email": "lucas.martin@example.com",    "phone": "555-0108", "signup_date": d(200), "loyalty_tier": "standard", "total_orders": 2,  "account_flag": "none"},
    {"customer_id": "CUST009", "name": "Charlotte Davis",   "email": "charlotte.davis@example.com", "phone": "555-0109", "signup_date": d(1500),"loyalty_tier": "platinum", "total_orders": 38, "account_flag": "none"},
    {"customer_id": "CUST010", "name": "James Wilson",      "email": "james.wilson@example.com",    "phone": "555-0110", "signup_date": d(380), "loyalty_tier": "silver",   "total_orders": 15, "account_flag": "none"},
    {"customer_id": "CUST011", "name": "Amelia Garcia",     "email": "amelia.garcia@example.com",   "phone": "555-0111", "signup_date": d(700), "loyalty_tier": "gold",     "total_orders": 12, "account_flag": "none"},
    {"customer_id": "CUST012", "name": "Benjamin Lee",      "email": "benjamin.lee@example.com",    "phone": "555-0112", "signup_date": d(150), "loyalty_tier": "standard", "total_orders": 1,  "account_flag": "none"},
    {"customer_id": "CUST013", "name": "Harper Brown",      "email": "harper.brown@example.com",    "phone": "555-0113", "signup_date": d(500), "loyalty_tier": "silver",   "total_orders": 6,  "account_flag": "none"},
    {"customer_id": "CUST014", "name": "Henry Clark",       "email": "henry.clark@example.com",     "phone": "555-0114", "signup_date": d(260), "loyalty_tier": "standard", "total_orders": 3,  "account_flag": "none"},
    {"customer_id": "CUST015", "name": "Evelyn Lewis",      "email": "evelyn.lewis@example.com",    "phone": "555-0115", "signup_date": d(980), "loyalty_tier": "platinum", "total_orders": 21, "account_flag": "none"},
]

ORDERS = [
    # order_id, customer_id, product, category, order_date_offset, delivery_date_offset(None=not delivered), amount, shipping, status
    {"order_id": "ORD1001", "customer_id": "CUST001", "product_name": "Wireless Earbuds",        "category": "electronics", "order_date": d(15), "delivery_date": d(10), "amount": 79.99,  "shipping_amount": 5.99, "status": "delivered"},
    {"order_id": "ORD1002", "customer_id": "CUST001", "product_name": "Bluetooth Speaker",        "category": "electronics", "order_date": d(45), "delivery_date": d(40), "amount": 59.99,  "shipping_amount": 0.0,  "status": "delivered"},
    {"order_id": "ORD1003", "customer_id": "CUST002", "product_name": "Smart Watch",               "category": "electronics", "order_date": d(22), "delivery_date": d(18), "amount": 199.00, "shipping_amount": 0.0,  "status": "delivered"},
    {"order_id": "ORD1004", "customer_id": "CUST003", "product_name": "Office Chair",              "category": "furniture",   "order_date": d(30), "delivery_date": d(25), "amount": 249.00, "shipping_amount": 19.99,"status": "delivered"},
    {"order_id": "ORD1005", "customer_id": "CUST004", "product_name": "Skincare Gift Set",          "category": "beauty",      "order_date": d(13), "delivery_date": d(10), "amount": 64.50,  "shipping_amount": 0.0,  "status": "delivered"},
    {"order_id": "ORD1006", "customer_id": "CUST005", "product_name": "Denim Jacket",               "category": "apparel",     "order_date": d(8),  "delivery_date": d(5),  "amount": 89.00,  "shipping_amount": 0.0,  "status": "delivered"},
    {"order_id": "ORD1007", "customer_id": "CUST006", "product_name": "Organic Produce Box",        "category": "grocery",     "order_date": d(6),  "delivery_date": d(3),  "amount": 45.00,  "shipping_amount": 7.99, "status": "delivered"},
    {"order_id": "ORD1008", "customer_id": "CUST006", "product_name": "Snack Variety Pack",         "category": "grocery",     "order_date": d(6),  "delivery_date": d(3),  "amount": 22.00,  "shipping_amount": 4.99, "status": "delivered"},
    {"order_id": "ORD1009", "customer_id": "CUST007", "product_name": "Clearance Lamp",             "category": "final_sale",  "order_date": d(4),  "delivery_date": d(2),  "amount": 34.99,  "shipping_amount": 0.0,  "status": "delivered"},
    {"order_id": "ORD1010", "customer_id": "CUST008", "product_name": "Mystery Novel Box Set",      "category": "books",       "order_date": d(25), "delivery_date": d(20), "amount": 42.00,  "shipping_amount": 0.0,  "status": "delivered"},
    {"order_id": "ORD1011", "customer_id": "CUST009", "product_name": "4K Action Camera",           "category": "electronics", "order_date": d(32), "delivery_date": d(28), "amount": 329.00, "shipping_amount": 0.0,  "status": "delivered"},
    {"order_id": "ORD1012", "customer_id": "CUST010", "product_name": "Running Shoes",              "category": "apparel",     "order_date": d(8),  "delivery_date": d(5),  "amount": 110.00, "shipping_amount": 0.0,  "status": "delivered"},
    {"order_id": "ORD1013", "customer_id": "CUST011", "product_name": "Coffee Table",               "category": "furniture",   "order_date": d(9),  "delivery_date": d(5),  "amount": 189.00, "shipping_amount": 29.99,"status": "delivered"},
    {"order_id": "ORD1014", "customer_id": "CUST012", "product_name": "Gaming Mouse",               "category": "electronics", "order_date": d(3),  "delivery_date": None,  "amount": 49.99,  "shipping_amount": 0.0,  "status": "cancelled"},
    {"order_id": "ORD1015", "customer_id": "CUST013", "product_name": "Wool Sweater",               "category": "apparel",     "order_date": d(40), "delivery_date": d(35), "amount": 75.00,  "shipping_amount": 0.0,  "status": "refunded"},
    {"order_id": "ORD1016", "customer_id": "CUST014", "product_name": "Face Moisturizer",           "category": "beauty",      "order_date": d(12), "delivery_date": d(9),  "amount": 28.00,  "shipping_amount": 0.0,  "status": "delivered"},
    {"order_id": "ORD1017", "customer_id": "CUST015", "product_name": "Cookbook Collection",        "category": "books",       "order_date": d(55), "delivery_date": d(50), "amount": 38.00,  "shipping_amount": 0.0,  "status": "delivered"},
    {"order_id": "ORD1018", "customer_id": "CUST002", "product_name": "Flannel Shirt",              "category": "apparel",     "order_date": d(13), "delivery_date": d(10), "amount": 39.99,  "shipping_amount": 0.0,  "status": "delivered"},
    {"order_id": "ORD1019", "customer_id": "CUST007", "product_name": "Noise-Cancelling Headphones","category": "electronics", "order_date": d(8),  "delivery_date": d(5),  "amount": 159.00, "shipping_amount": 0.0,  "status": "delivered"},
    {"order_id": "ORD1020", "customer_id": "CUST009", "product_name": "Fresh Seafood Pack",         "category": "grocery",     "order_date": d(4),  "delivery_date": d(1),  "amount": 52.00,  "shipping_amount": 9.99, "status": "delivered"},
]

# Pre-seeded refund history so CUST010 trips the `frequent_returner` rule
# (more than 5 approved refunds in the trailing 90 days).
FREQUENT_RETURNER_HISTORY = [
    {
        "order_id": "ORD1012",
        "customer_id": "CUST010",
        "reason": "Didn't like the fit",
        "claimed_defective": False,
        "decision": "approved",
        "refund_amount": 60.00 + i,
        "explanation": "Historical seed record for demo purposes.",
    }
    for i in range(6)
]


def main():
    sb = get_supabase()

    print(f"Seeding {len(CUSTOMERS)} customers...")
    sb.table("customers").upsert(CUSTOMERS).execute()

    print(f"Seeding {len(ORDERS)} orders...")
    sb.table("orders").upsert(ORDERS).execute()

    print(f"Seeding {len(FREQUENT_RETURNER_HISTORY)} historical refund records for CUST010...")
    sb.table("refund_requests").insert(FREQUENT_RETURNER_HISTORY).execute()

    print("Done. Database is ready.")


if __name__ == "__main__":
    main()
