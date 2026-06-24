# E-Commerce Refund Policy — Internal Reference (v1.0)

This document is the source of truth for the Refund Agent. All refund tools
implement these rules programmatically. Decisions must never deviate from
this policy.

## 1. Eligibility Window by Category (from delivery date)

| Category   | Standard Window | Condition Required              |
|------------|-----------------|----------------------------------|
| electronics| 15 days         | Unopened, or defective           |
| apparel    | 30 days         | Unworn, tags attached            |
| beauty     | 7 days          | Unopened/unused (hygiene rule)   |
| furniture  | 30 days         | Original packaging               |
| books      | 30 days         | Any condition                    |
| grocery    | 0 days          | No refunds unless damaged/defective on arrival |
| final_sale | 0 days          | **No refunds ever**, no exceptions, no overrides |

## 2. Defective / Damaged-on-Arrival Override

If the customer states the item arrived **defective or damaged**, and the
category is **not** `final_sale`:

- The eligibility window extends to **90 days** from delivery, regardless
  of the category's standard window.
- The refund is **full** (no restocking fee), and original shipping costs
  are refunded too.
- Photo proof should be requested by the agent but is not required to
  approve the refund.

## 3. Loyalty Tier Grace Extensions

Added on top of the category's standard window. Does **not** apply to
categories with a 0-day standard window (`final_sale`, `grocery`) — loyalty
status does not create a return right where the category otherwise has
none for non-defective items. (The defective/damaged override in Section 2
is independent and still applies to `grocery`.)

| Loyalty Tier | Extra Grace Days | Restocking Fee Waived? |
|--------------|-------------------|--------------------------|
| standard     | +0 days           | No                       |
| silver       | +5 days           | No                       |
| gold         | +10 days          | Yes                      |
| platinum     | +15 days          | Yes (+ priority handling)|

## 4. Restocking Fees

- `furniture`: 15% restocking fee on non-defective returns — unless waived
  by loyalty tier (gold/platinum) or the item is defective/damaged.
- All other categories: 0% restocking fee.

## 5. Order Status Requirements

- Only orders with status `delivered` may be evaluated for refund.
- Orders already `refunded` cannot be refunded again — deny.
- Orders `cancelled` or `in_transit` are **not** handled by this agent.
  They must be escalated to a human agent.

## 6. Fraud & Abuse Flags

- Customers flagged `fraud_watch` → **always escalate**, never auto-approve
  or auto-deny, regardless of how the eligibility math works out.
- Customers who have **more than 5 approved refunds in the trailing 90
  days** (`frequent_returner`) → **always escalate** for manual review,
  regardless of otherwise-passing eligibility.

## 7. Refund Amount Calculation

1. Base = order amount.
2. Subtract the restocking fee percentage (Section 4) when applicable.
3. Original shipping fees are **non-refundable**, UNLESS the item was
   defective/damaged or the wrong item was shipped — in which case
   shipping is refunded in full as well.

## 8. Proof of Purchase

A valid `order_id` that matches the customer's account in the CRM/orders
table constitutes proof of purchase. If the order cannot be matched to the
customer, **deny** and ask for a valid order number.

## 9. Decision Authority

The agent may autonomously:

- **APPROVE** when all eligibility checks pass and no escalation flags
  apply.
- **DENY** when the window has expired, the category disallows refunds,
  the order is already refunded, or the order/customer cannot be verified.

The agent **must ESCALATE** (never approve or deny outright) when:

- The customer is flagged `fraud_watch` or qualifies as `frequent_returner`.
- The order status is anything other than `delivered` or `refunded`.
- The request involves something this policy doesn't clearly address
  (e.g. partial refunds, goodwill exceptions, price-match requests).
