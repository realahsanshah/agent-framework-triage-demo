"""Triage classifier: decides which specialist a message belongs to.

Kept as plain, deterministic keyword matching rather than an LLM call so the
routing decision is fast, free, and easy to reason about in a demo. Swapping
this for an LLM-based classifier later is a drop-in change -- the workflow
graph in workflow.py doesn't care how `classify` makes its decision.
"""

from dataclasses import dataclass

BILLING_KEYWORDS = ("charge", "charged", "refund", "balance", "bill", "payment", "invoice")
TECH_KEYWORDS = ("restart", "down", "outage", "error", "status", "not working", "vpn", "login")


@dataclass
class RoutedMessage:
    """A user message plus the triage decision, passed between workflow nodes."""

    text: str
    category: str  # "billing" | "tech" | "unknown"


def classify(text: str) -> str:
    lowered = text.lower()
    if any(keyword in lowered for keyword in BILLING_KEYWORDS):
        return "billing"
    if any(keyword in lowered for keyword in TECH_KEYWORDS):
        return "tech"
    return "unknown"
