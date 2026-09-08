"""Streamlit chat UI for the triage workflow.

Run with: streamlit run src/app.py

This is a thin presentation layer over the same `workflow_agent` used by
main.py -- it builds the workflow once per browser session, keeps one
`AgentSession` alive in `st.session_state` for the whole conversation, and
renders each turn's triage category alongside the specialist's reply so the
routing decision stays visible.
"""

import asyncio
from typing import Any

import streamlit as st
from agent_framework import AgentResponse, AgentSession, WorkflowAgent

from triage import classify
from workflow import build_workflow


@st.cache_resource
def get_workflow_agent() -> WorkflowAgent:
    return build_workflow().as_agent(name="triage_workflow")


def get_session() -> AgentSession:
    if "session" not in st.session_state:
        st.session_state.session = get_workflow_agent().create_session()
    session: AgentSession = st.session_state.session
    return session


def get_history() -> list[tuple[str, str]]:
    if "history" not in st.session_state:
        st.session_state.history = []
    history: list[tuple[str, str]] = st.session_state.history
    return history


async def run_turn(prompt: str, session: AgentSession) -> AgentResponse[Any]:
    return await get_workflow_agent().run(prompt, session=session)


st.set_page_config(page_title="Agent Framework Triage Demo")
st.title("Billing / Tech Support Triage")
st.caption("Microsoft Agent Framework: WorkflowBuilder + ChatAgent + AgentSession")

for role, text in get_history():
    st.chat_message(role).write(text)

if prompt := st.chat_input("Describe your issue..."):
    st.chat_message("user").write(prompt)
    get_history().append(("user", prompt))

    category = classify(prompt)
    with st.chat_message("assistant"):
        with st.spinner(f"Routing to {category} specialist..."):
            response = asyncio.run(run_turn(prompt, get_session()))
        st.caption(f"triage category: {category}")
        st.write(response.text)
    get_history().append(("assistant", response.text))
