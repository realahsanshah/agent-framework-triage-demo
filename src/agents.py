"""The two specialist ChatAgents.

`Agent` is Agent Framework's ChatAgent-equivalent: a chat client + system
instructions + a set of callable tools (+ optional middleware). It has no
routing knowledge of its own -- that lives in workflow.py.
"""

import os

from agent_framework import Agent
from agent_framework.openai import OpenAIChatCompletionClient
from dotenv import load_dotenv

from middleware import logging_middleware
from tools import check_balance, check_system_status, issue_refund, restart_service

load_dotenv()


def _build_client() -> OpenAIChatCompletionClient:
    return OpenAIChatCompletionClient(
        model=os.environ["OPENROUTER_MODEL"],
        api_key=os.environ["OPENROUTER_API_KEY"],
        base_url=os.environ.get("OPENROUTER_BASE_URL", "https://openrouter.ai/api/v1"),
        default_headers={
            "HTTP-Referer": "https://github.com/agent-framework-triage-demo",
            "X-Title": "Agent Framework Triage Demo",
        },
    )


def build_billing_agent() -> Agent:
    return Agent(
        client=_build_client(),
        name="billing_agent",
        instructions=(
            "You are a billing support specialist. Help customers with charges, "
            "balances, and refunds using your tools. Always look up the account "
            "before issuing a refund. Keep replies short and concrete."
        ),
        tools=[check_balance, issue_refund],
        middleware=[logging_middleware],
    )


def build_tech_agent() -> Agent:
    return Agent(
        client=_build_client(),
        name="tech_agent",
        instructions=(
            "You are a technical support specialist. Help customers diagnose and "
            "fix service issues using your tools. Check status before restarting "
            "a service. Keep replies short and concrete."
        ),
        tools=[restart_service, check_system_status],
        middleware=[logging_middleware],
    )
