"""Wires the two specialist agents into a WorkflowBuilder graph.

WorkflowBuilder builds a directed graph of executors. Our graph has one
custom node (`triage`, a plain async function turned into an executor via
the `@executor` decorator) that classifies the incoming conversation,
followed by two built-in `AgentExecutor` nodes that wrap `billing_agent` and
`tech_agent` so they can sit directly in the graph. A switch-case edge group
routes to whichever specialist's `Case` condition matches, falling back to a
small clarification node via `Default`.
"""

from typing import Never

from agent_framework import (
    AgentExecutor,
    Case,
    Default,
    Message,
    Workflow,
    WorkflowBuilder,
    WorkflowContext,
    executor,
)

from agents import build_billing_agent, build_tech_agent
from triage import classify


@executor(id="triage")
async def triage(messages: list[Message], ctx: WorkflowContext[list[Message]]) -> None:
    category = classify(messages[-1].text)
    print(f"[triage] classified message as: {category}")
    await ctx.send_message(messages)


@executor(id="unclear_intent")
async def unclear_intent(messages: list[Message], ctx: WorkflowContext[Never, str]) -> None:
    await ctx.yield_output(
        "I'm not sure whether this is a billing or a technical issue -- could you clarify?"
    )


def _is_billing(messages: list[Message]) -> bool:
    return classify(messages[-1].text) == "billing"


def _is_tech(messages: list[Message]) -> bool:
    return classify(messages[-1].text) == "tech"


def build_workflow() -> Workflow:
    billing_node = AgentExecutor(build_billing_agent(), id="billing_node")
    tech_node = AgentExecutor(build_tech_agent(), id="tech_node")

    return (
        WorkflowBuilder(start_executor=triage)
        .add_switch_case_edge_group(
            triage,
            [
                Case(condition=_is_billing, target=billing_node),
                Case(condition=_is_tech, target=tech_node),
                Default(target=unclear_intent),
            ],
        )
        .build()
    )
