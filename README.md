# AI Customer Support Agent — Refund Processing

A fully functional AI customer support agent that approves, denies, or
escalates e-commerce refund requests strictly according to a written
policy — with a LangGraph tool-calling agent loop, a Supabase-backed CRM,
a Streamlit chat UI with voice input/output, and an admin dashboard that
shows the agent's reasoning in real time.

## Architecture

```
┌─────────────────────────┐        ┌──────────────────────────┐
│   streamlit_app.py       │        │  pages/1_Admin_Dashboard │
│   (customer chat + mic)  │        │  (live reasoning trace,  │
│                           │        │   decisions, CRM browser)│
└─────────────┬─────────────┘        └─────────────┬─────────────┘
              │                                     │
              ▼                                     ▼
   backend/agent_graph.py (LangGraph)      backend/logger.py
   ┌─────────┐ tool_calls? ┌────────┐            │
   │  agent  │────────────▶│ tools  │            │
   │ (GPT)   │◀────────────│ (run)  │            │
   └─────────┘   results   └────────┘            │
        │                       │                 │
        ▼                       ▼                 ▼
  backend/tools.py  ──────▶ backend/policy_engine.py   agent_logs table
   (lookup_customer,         (pure-python rules engine        │
    check_refund_eligibility, mirroring data/refund_policy.md)│
    log_refund_decision, …)                                  │
        │                                                     │
        ▼                                                     ▼
                      Supabase (customers, orders,
                       refund_requests, agent_logs)
```

**Why this shape:** the LLM only ever *decides which tool to call next and
narrates results in plain language*. Every fact (eligibility window math,
restocking fees, fraud/escalation flags, refund totals) is computed by the
deterministic `policy_engine.py`, not guessed by the model. That keeps
decisions auditable and reproducible — re-running the same order through
the engine always gives the same answer, and every decision is written to
`refund_requests` with the exact reasoning that produced it.

## What's inside

| Path | What it does |
|---|---|
| `data/refund_policy.md` | The strict, written refund policy (source of truth) |
| `db/schema.sql` | Supabase table definitions |
| `db/seed_data.py` | Seeds 15 CRM customer profiles + 20 orders covering every policy branch |
| `backend/policy_engine.py` | Deterministic rules engine mirroring the policy doc |
| `backend/tools.py` | LangChain tools the agent calls (CRM lookups, eligibility checks, logging) |
| `backend/agent_graph.py` | The LangGraph agent loop (`agent` ⇄ `tools`) + system prompt |
| `backend/logger.py` | Writes/reads the step-by-step reasoning trace |
| `voice/voice_pipeline.py` | OpenAI Whisper (STT) + OpenAI TTS (speech out) |
| `streamlit_app.py` | Customer-facing chat UI with mic input / spoken replies |
| `pages/1_Admin_Dashboard.py` | Real-time reasoning trace viewer, decision audit log, CRM browser |

## Setup

### 1. Create the Supabase project & schema

1. Create a free project at [supabase.com](https://supabase.com).
2. Open the SQL Editor and run the contents of `db/schema.sql`.
3. Grab your Project URL and API key from **Settings → API**.

### 2. Configure environment variables

```bash
cp .env.example .env
# then edit .env with your SUPABASE_URL, SUPABASE_KEY, and OPENAI_API_KEY
```

### 3. Install dependencies

```bash
python -m venv venv && source venv/bin/activate   # optional but recommended
pip install -r requirements.txt
```

### 4. Seed the CRM data

```bash
python db/seed_data.py
```

This inserts 15 customers (standard/silver/gold/platinum tiers, one
`fraud_watch` account) and 20 orders deliberately spanning every branch of
the policy: inside/outside the return window, loyalty-grace saves, a
defective-item override, a `final_sale` item, a cancelled order, an
already-refunded order, and a customer (`CUST010`) with enough prior
approved refunds to trip the `frequent_returner` escalation rule.

### 5. Run the app

```bash
streamlit run streamlit_app.py
```

This launches the customer chat at the root URL. The **Admin Dashboard**
appears automatically as a second page in Streamlit's sidebar navigation
(or visit `.../Admin_Dashboard`).

## Using it

**Customer chat (`streamlit_app.py`):**
- Type a message, or click the mic icon in the sidebar to record a voice
  message (transcribed via Whisper).
- Toggle "Speak replies aloud" to have responses read back via TTS.
- The sidebar lists the 15 seeded demo emails so you can try different
  loyalty tiers / the fraud-flagged account without leaving the app.
- A typical flow: give your email → name the order (or ask the agent to
  list your orders) → say whether the item is defective or you just
  changed your mind → get an approve/deny/escalate decision with a plain-
  language explanation.

**Admin Dashboard (`pages/1_Admin_Dashboard.py`):**
- **Live Reasoning Trace** — pick a session ID (shown in the customer
  app's sidebar) to watch every step: the user's message, the agent's
  tool calls with arguments, each tool's JSON result, and the final
  reply. Auto-refreshes every few seconds. There's also a "global
  activity feed" toggle to watch all sessions at once.
- **Refund Decisions** — the full audit trail from `refund_requests`,
  with approve/deny/escalate counts and total dollars refunded.
- **CRM Browser** — raw `customers` and `orders` tables for reference.

## The policy, in brief

See `data/refund_policy.md` for the full text. Summary:

- Return windows vary by category (15 days electronics, 30 days
  apparel/furniture/books, 7 days beauty, 0 days grocery/final_sale).
- A claimed defective/damaged item extends the window to 90 days with no
  restocking fee and refundable shipping — except `final_sale`, which is
  never refundable under any circumstance.
- Loyalty tiers add grace days (silver +5, gold +10, platinum +15) and
  gold/platinum waive restocking fees — but grace days don't apply to
  categories with a 0-day base window (grocery, final_sale), since loyalty
  status shouldn't create a return right that category doesn't have.
- `fraud_watch` accounts and `frequent_returner` customers (>5 approved
  refunds in 90 days) are always escalated to a human, never auto-decided.
- Non-`delivered` orders (cancelled, in-transit) are escalated; already-
  `refunded` orders are denied outright.

## Design notes / trade-offs

- **LLM provider:** OpenAI (`gpt-4o-mini` by default, configurable via
  `OPENAI_MODEL`) for both the agent and the voice pipeline, so there's a
  single API key to manage.
- **Voice pipeline (bonus):** kept intentionally simple — OpenAI Whisper
  for speech-to-text and OpenAI TTS for speech-out, both behind the same
  key. This is **not** full-duplex/streaming like the OpenAI Realtime API,
  ElevenLabs, or LiveKit would give you; it's record → transcribe → run
  the agent → (optionally) synthesize the reply. `voice/voice_pipeline.py`
  is a thin, swappable module — replacing it with a Realtime API session
  wouldn't require touching `agent_graph.py` or the policy tools.
- **Memory:** LangGraph's `MemorySaver` checkpointer keys conversation
  state by `session_id` (the Streamlit session's thread id), so multi-turn
  context (e.g., "yes, that one" after listing orders) works within a
  session. Memory is in-process — restarting the Streamlit server clears
  conversation memory (but not the Supabase data or audit logs).
- **RLS:** disabled in `db/schema.sql` for demo simplicity. In a real
  deployment, add row-level security policies and use a backend-only
  service role key, never exposed to a browser-side client.
- **Auditability:** `policy_engine.py` is pure, dependency-free Python —
  you can unit test refund math without touching Supabase or an LLM (see
  the inline examples in that file's docstrings for the rule structure).

## Extending this

- **Swap the LLM:** change `OPENAI_MODEL` in `.env`, or replace
  `ChatOpenAI` in `backend/agent_graph.py` with `ChatAnthropic` /
  another LangChain chat model — the tool-calling interface is the same.
- **Swap the voice backend:** implement the same two functions
  (`transcribe_audio`, `synthesize_speech`) in `voice/voice_pipeline.py`
  against ElevenLabs, LiveKit, or the OpenAI Realtime API for streaming,
  lower-latency voice.
- **Add new policy rules:** edit `data/refund_policy.md` for humans, and
  mirror the change in `backend/policy_engine.py` for the engine — keep
  both in sync, since the engine is what actually runs.
