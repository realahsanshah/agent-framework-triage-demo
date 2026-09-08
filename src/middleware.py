"""Logging middleware for the specialist agents.

Agent Framework middleware wraps every agent invocation: you get a context
object *before* the model/tooling runs, you call `call_next()` yourself to
let it run, and you can inspect (or override) `context.result` afterwards.
This is the same "before/after" shape as Express/ASP.NET middleware, applied
to an agent call instead of an HTTP request.
"""

from collections.abc import Awaitable, Callable

from agent_framework import AgentContext, AgentResponse, agent_middleware


@agent_middleware
async def logging_middleware(
    context: AgentContext,
    call_next: Callable[[], Awaitable[None]],
) -> None:
    agent_name = context.agent.name or "agent"
    print(f"[middleware] -> {agent_name} received {len(context.messages)} message(s)")

    await call_next()

    reply_preview = ""
    if isinstance(context.result, AgentResponse):
        reply_preview = context.result.text[:80]
    print(f"[middleware] <- {agent_name} replied: {reply_preview!r}")
