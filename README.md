# Agent Framework Triage Demo

A multi-agent billing / tech-support triage system built on **Microsoft Agent
Framework** (Python) -- the framework that replaces Semantic Kernel for
agentic workloads.

## What it does

A user message goes through a `WorkflowBuilder` graph:

```
User message
    |
    v
triage (keyword classifier)
    |
    +--"billing"--> guardrails_middleware --> billing_agent  (check_balance, issue_refund)
    +--"tech"-----> guardrails_middleware --> tech_agent     (check_system_status, restart_service)
    +--default----> unclear_intent (asks the user to clarify)
```

- `triage` is a plain async function decorated with `@executor`, that reads
  the latest message and classifies it with a keyword match. It doesn't call
  the model -- the routing decision is fast and deterministic.
- `billing_agent` and `tech_agent` are `Agent` instances (Agent Framework's
  ChatAgent-equivalent: a chat client + instructions + tools), wrapped as
  `AgentExecutor` nodes so they can sit directly in the graph.
- A `SwitchCaseEdgeGroup` (`add_switch_case_edge_group`) routes to whichever
  `Case`'s condition matches the classification, or to the `Default` node.
- `Workflow.as_agent()` wraps the whole graph so it exposes the same
  `create_session()` / `run(messages, session=...)` interface as a single
  `Agent` -- a caller can't tell a multi-agent workflow apart from a plain
  chat agent.
- Two `agent_middleware`-decorated functions are attached to both
  specialists: `logging_middleware` logs before/after each agent invocation,
  and `guardrails_middleware` runs [NeMo Guardrails](https://github.com/NVIDIA-NeMo/Guardrails)
  checks *before* the specialist agent (or its tools) ever sees the message
  -- see "Guardrails" below.
- Model access goes through `OpenAIChatCompletionClient` pointed at
  OpenRouter's OpenAI-compatible endpoint (`base_url` override), so any
  OpenRouter model -- including free ones -- works without code changes.

## Guardrails

`guardrails_middleware` ([src/guardrails.py](src/guardrails.py)) wraps each
specialist agent the same way `logging_middleware` does -- same
`call_next()`-interceptor shape -- but it can refuse to call `call_next()` at
all. Two NeMo Guardrails checks run first, defined in
[guardrails/config.yml](guardrails/config.yml) and
[guardrails/rails/*.co](guardrails/rails):

1. **Dialog rails** -- Colang "common expression" flows
   (`define user express greeting`, `define user attempt jailbreak`, ...)
   matched by embedding similarity against example utterances, no LLM call
   needed. A match (greeting, goodbye, jailbreak-style phrasing) returns a
   canned reply directly -- the specialist agent never runs.
2. **Input rails** -- `self check input`, an LLM-based policy check
   (off-topic / instruction-override / profanity) that only runs -- and only
   costs a model call -- if the dialog rails above didn't already resolve
   the message.

Either check firing replaces the middleware's `context.result` and returns
without calling `call_next()`, exactly the short-circuit the middleware
pattern is built for. A message that passes both checks reaches the
specialist agent completely normally.

Guardrails' embedding matching (used for the dialog rails) downloads a small
ONNX model from Hugging Face on first run and caches it locally --
`fastembed` is the local, torch-free embedding provider NeMo Guardrails uses
by default.

Run it:

```bash
python -m venv .venv
.venv/Scripts/activate        # or: source .venv/bin/activate
pip install -e ".[dev,ui]"
cp .env.example .env          # then fill in OPENROUTER_API_KEY
python src/main.py            # CLI demo
streamlit run src/app.py      # chat UI
```

## Why Agent Framework specifically

Semantic Kernel and the standalone "AutoGen" line have been merged into a
single Python package, **Agent Framework**, which is now Microsoft's
recommended path for both simple chat agents and multi-agent orchestration.
The concepts map directly onto what's already familiar from OpenAI's Agents
SDK and Google's ADK:

| Concept | OpenAI Agents SDK | Google ADK | Agent Framework |
|---|---|---|---|
| Single agent | `Agent` | `Agent` | `Agent` (ChatAgent) |
| Tool calling | Python function + schema inference | Python function | Python function + schema inference |
| Multi-turn state | `Session` | session/`Runner` | `AgentSession` |
| Orchestration | handoffs | multi-agent workflows | `WorkflowBuilder` graph |
| Cross-cutting logic | hooks | callbacks | `middleware` |

The main conceptual shift from Semantic Kernel is that orchestration is now
an explicit **graph** (`WorkflowBuilder`, executors, edges) rather than
planners/plugins, which makes multi-agent control flow (routing, fan-out,
fan-in) something you can literally draw and unit-test as a graph, instead of
something an LLM planner decides at runtime.

## What I'd add with more time

- **Checkpointing** (`CheckpointStorage`) so an in-progress workflow run
  survives a process restart -- out of scope per the brief, but the workflow
  already accepts a `checkpoint_storage` argument, so it's a small addition.
- **DevUI** for visually stepping through a run instead of reading stdout.
- **LLM-based triage** instead of keyword matching, with a fallback to the
  keyword classifier if the model call fails.
- **Real backends** for `tools.py` instead of in-memory mock data.
- Tests around `triage.classify` and the workflow's routing decisions.
- **Output rails** on the guardrails side -- e.g. a `self check output` /
  sensitive-data-masking pass over what the specialist agent replies with,
  symmetric to the input-side checks that exist today.

## Learning checkpoints (for walking through the code out loud)

- **`Agent`** ([src/agents.py](src/agents.py)): a chat client + instructions
  + tools + optional middleware. No routing knowledge of its own.
- **`WorkflowBuilder`** ([src/workflow.py](src/workflow.py)): builds a graph
  of executors and edges; a `SwitchCaseEdgeGroup` is how content-based
  routing ("triage") is expressed declaratively.
- **`AgentSession`** ([src/main.py](src/main.py)): a lightweight handle
  (mostly just an ID); the actual conversation history is owned by whichever
  agent's `create_session()` you called and is threaded through every
  `run()` call on that session -- which is why `billing_agent` sees the full
  conversation on turn 2 even though only `workflow_agent.create_session()`
  was ever called.
- **`guardrails_middleware`** ([src/guardrails.py](src/guardrails.py)): the
  same `call_next()` interceptor shape as `logging_middleware`, but it can
  choose not to call `call_next()` at all -- a NeMo Guardrails check firing
  short-circuits straight to a canned `context.result`, so the specialist
  agent and its tools never run for that message.
