"""
LangGraph agent loop for the refund agent.

Graph shape:

    START -> agent -> (tool_calls present?) -> tools -> agent -> ... -> END

The `agent` node calls the LLM (bound to the refund tools). If it returns
tool calls, we route to the `tools` node, which executes them and routes
back to `agent`. If it returns a plain text answer, we route to END.

Every step (user message, agent tool-call intent, tool execution result,
final natural-language response) is persisted via backend.logger so the
admin dashboard can render a real-time reasoning trace per session.
"""
import json
from typing import Annotated, TypedDict

from langchain_core.messages import AIMessage, HumanMessage, SystemMessage, ToolMessage
from langchain_openai import ChatOpenAI
from langgraph.checkpoint.memory import MemorySaver
from langgraph.graph import END, StateGraph
from langgraph.graph.message import add_messages

from backend.config import config
from backend.logger import log_step
from backend.tools import ALL_TOOLS

TOOL_MAP = {t.name: t for t in ALL_TOOLS}

SYSTEM_PROMPT = """You are an AI customer support agent for an e-commerce store. You \
process or deny refund requests strictly according to company policy, using tools \
for every factual claim — never invent customer or order data.

Workflow:
1. Verify identity: if you don't already know the customer's email, ask for it, \
then call lookup_customer.
2. Identify the order: if the customer doesn't know their order_id, call \
get_customer_orders to help them find it, then get_order_details to confirm it.
3. Ask whether the item arrived defective/damaged/wrong, or whether this is a \
change-of-mind / fit / preference return. This determines claimed_defective.
4. Call check_refund_eligibility(order_id, customer_id, claimed_defective).
5. ALWAYS also call check_customer_risk_flags(customer_id). If requires_escalation \
is true, you MUST escalate regardless of what check_refund_eligibility said — do not \
approve or deny in that case.
6. If approving, call calculate_refund_amount using the restocking_fee_pct and \
defective_override_applied fields returned by check_refund_eligibility.
7. ALWAYS call log_refund_decision exactly once at the end with the final outcome \
(approved / denied / escalated), even for denials and escalations (refund_amount=0 \
in that case).
8. Explain the decision to the customer in warm, plain language, briefly citing the \
relevant reasoning (return window, category, loyalty tier, fees) — never dump raw \
JSON or internal tool names at the customer.

Hard rules:
- Never approve or quote a refund amount without first calling both \
check_refund_eligibility AND check_customer_risk_flags.
- If escalation is required, tell the customer their case is being escalated to a \
human specialist for manual review within 1-2 business days. Do not reveal the \
specific internal flag (fraud_watch / frequent_returner) — just say "manual review".
- Be concise, professional, and empathetic. One topic/order at a time.
"""


class AgentState(TypedDict):
    messages: Annotated[list, add_messages]
    session_id: str


def _build_llm():
    return ChatOpenAI(
        model=config.OPENAI_MODEL,
        temperature=0,
        api_key=config.OPENAI_API_KEY,
    ).bind_tools(ALL_TOOLS)


def _is_json(value: str) -> bool:
    try:
        json.loads(value)
        return True
    except (TypeError, ValueError):
        return False


def build_agent_graph():
    llm_with_tools = _build_llm()

    def agent_node(state: AgentState):
        session_id = state["session_id"]
        messages = state["messages"]
        if not any(isinstance(m, SystemMessage) for m in messages):
            messages = [SystemMessage(content=SYSTEM_PROMPT)] + list(messages)

        response = llm_with_tools.invoke(messages)

        if response.tool_calls:
            if response.content:
                log_step(session_id, "agent_thought", response.content, node_name="agent")
            for tc in response.tool_calls:
                log_step(
                    session_id,
                    "tool_call",
                    json.dumps({"tool": tc["name"], "args": tc["args"]}),
                    node_name="agent",
                )
        else:
            log_step(session_id, "final_response", response.content, node_name="agent")

        return {"messages": [response]}

    def tools_node(state: AgentState):
        session_id = state["session_id"]
        last_message = state["messages"][-1]
        outputs = []
        for tc in last_message.tool_calls:
            tool_fn = TOOL_MAP.get(tc["name"])
            if tool_fn is None:
                result = json.dumps({"error": f"Unknown tool '{tc['name']}'."})
            else:
                try:
                    result = tool_fn.invoke(tc["args"])
                except Exception as exc:  # noqa: BLE001
                    result = json.dumps({"error": str(exc)})

            log_step(
                session_id,
                "tool_result",
                json.dumps({"tool": tc["name"], "result": json.loads(result) if _is_json(result) else result}),
                node_name="tools",
            )
            outputs.append(ToolMessage(content=str(result), tool_call_id=tc["id"], name=tc["name"]))
        return {"messages": outputs}

    def route(state: AgentState):
        last_message = state["messages"][-1]
        if isinstance(last_message, AIMessage) and last_message.tool_calls:
            return "tools"
        return END

    graph = StateGraph(AgentState)
    graph.add_node("agent", agent_node)
    graph.add_node("tools", tools_node)
    graph.set_entry_point("agent")
    graph.add_conditional_edges("agent", route, {"tools": "tools", END: END})
    graph.add_edge("tools", "agent")

    return graph.compile(checkpointer=MemorySaver())


def run_agent_turn(graph, session_id: str, user_text: str) -> str:
    """Run one user turn through the graph and return the agent's reply text."""
    log_step(session_id, "user_message", user_text)
    thread_config = {"configurable": {"thread_id": session_id}}
    result = graph.invoke(
        {"messages": [HumanMessage(content=user_text)], "session_id": session_id},
        config=thread_config,
    )
    final_message = result["messages"][-1]
    return final_message.content
