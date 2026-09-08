"""Entry point: runs a multi-turn conversation through the triage workflow.

`Workflow.as_agent()` wraps the whole graph so it exposes the same
`create_session()` / `run(messages, session=...)` interface as a plain
`Agent` -- from the caller's point of view, a multi-agent workflow and a
single chat agent look identical.
"""

import asyncio

from workflow import build_workflow


async def main() -> None:
    workflow_agent = build_workflow().as_agent(name="triage_workflow")
    session = workflow_agent.create_session()

    turns = [
        "I was charged twice for my subscription, my customer id is cust_1",
        "make that a partial refund instead",
    ]

    for turn in turns:
        print(f"\nUser: {turn}")
        response = await workflow_agent.run(turn, session=session)
        print(f"Assistant: {response.text}")


if __name__ == "__main__":
    asyncio.run(main())
