"""NeMo Guardrails integration, exposed as Agent Framework middleware.

Same call_next() interceptor shape as logging_middleware (see middleware.py)
-- but here call_next() only runs once two NeMo Guardrails checks are done:

1. Dialog rails (guardrails/rails/*.co): "common expression" flows for
   greetings and jailbreak-style phrasing, matched by embedding similarity
   against example utterances -- no LLM call for the match itself.
2. Input rails (guardrails/config.yml): "self check input", an LLM-based
   policy check for off-topic/profanity/instruction-override attempts --
   only runs if step 1 didn't already resolve the message.

Either check firing replaces context.result with its own canned response and
returns without calling call_next(), so the specialist agent and its tools
never see that message.
"""

import os
from collections.abc import Awaitable, Callable
from pathlib import Path

from agent_framework import AgentContext, AgentResponse, Message, agent_middleware
from nemoguardrails import LLMRails, RailsConfig
from nemoguardrails.rails.llm.config import Model
from nemoguardrails.rails.llm.options import (
    GenerationOptions,
    GenerationResponse,
    RailStatus,
    RailType,
)

_CONFIG_DIR = Path(__file__).resolve().parent.parent / "guardrails"

# Names of the dialog flows defined in guardrails/rails/*.co -- used to tell
# "one of our common-expression flows fired" apart from NeMo's own generic
# fallback reply when nothing matches.
_DIALOG_FLOW_NAMES = {"greeting", "goodbye", "jailbreak attempt"}

_rails: LLMRails | None = None


def _as_response(text: str) -> AgentResponse:
    return AgentResponse(messages=[Message(role="assistant", contents=[text])])


def _build_rails() -> LLMRails:
    config = RailsConfig.from_path(str(_CONFIG_DIR))
    # Reuse the same OPENROUTER_* env vars agents.py builds its chat client
    # from, so the model powering guardrails checks isn't configured twice.
    config.models = [
        Model(
            type="main",
            engine="openai",
            model=os.environ["OPENROUTER_MODEL"],
            parameters={
                "base_url": os.environ.get("OPENROUTER_BASE_URL", "https://openrouter.ai/api/v1"),
                "api_key": os.environ["OPENROUTER_API_KEY"],
            },
        )
    ]
    return LLMRails(config)


def _get_rails() -> LLMRails:
    global _rails
    if _rails is None:
        _rails = _build_rails()
    return _rails


def _fired_dialog_flow(result: GenerationResponse) -> str | None:
    """Return the reply text if one of our named dialog flows fired, else None."""
    if not result.log or not result.log.activated_rails:
        return None
    activated = result.log.activated_rails
    fired = any(rail.type == "dialog" and rail.name in _DIALOG_FLOW_NAMES for rail in activated)
    if not fired:
        return None
    if isinstance(result.response, list) and result.response:
        return str(result.response[-1].get("content") or "") or None
    return str(result.response) if result.response else None


@agent_middleware
async def guardrails_middleware(
    context: AgentContext,
    call_next: Callable[[], Awaitable[None]],
) -> None:
    agent_name = context.agent.name or "agent"
    user_text = context.messages[-1].text
    rails = _get_rails()

    dialog_result = await rails.generate_async(
        messages=[{"role": "user", "content": user_text}],
        options=GenerationOptions(rails=["dialog"], log={"activated_rails": True}),
    )
    reply = _fired_dialog_flow(dialog_result)
    if reply is not None:
        print(f"[guardrails] dialog flow -> {agent_name}: {reply!r}")
        context.result = _as_response(reply)
        return  # short-circuit: call_next() never runs

    check = await rails.check_async(
        [{"role": "user", "content": user_text}],
        rail_types=[RailType.INPUT],
    )
    if check.status != RailStatus.PASSED:
        print(f"[guardrails] {check.status.name} ({check.rail}) -> {agent_name}: {check.content!r}")
        context.result = _as_response(check.content)
        return  # short-circuit: call_next() never runs

    await call_next()
