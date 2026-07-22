"""The codified deep-research workflow: a LangGraph fan-out/fan-in graph.

This is the workflow-versus-agent distinction made concrete. The shell is a fixed
workflow, decompose then fan out then synthesize, so it is a graph with predefined
edges. The one step you cannot enumerate, researching a sub-question, is an agentic
node: each parallel worker runs a research subagent in its own isolated context.

The graph:
    planner  --Send fan-out-->  worker (xN, parallel, isolated)  -->  synthesis
The planner decomposes the query into independent aspects; the Send API dispatches
one worker per aspect; each worker returns a compressed finding; the reducer fans
them back in; a single synthesis node writes one cited report (never in parallel).

Two triggers reach this workflow: a human starts it explicitly (`start_research`),
or the chat agent's router classifies a research-shaped ask and starts it. The
whole chain is visible in a `ResearchRun` the caller can print.
"""

from __future__ import annotations

import operator
from dataclasses import dataclass, field
from typing import Annotated, Callable, TypedDict

from langgraph.graph import END, START, StateGraph
from langgraph.types import Send

from ..llm import LLMClient, Message
from .subagent import make_research_subagent

_PLANNER_SYSTEM = (
    "You are a research planner. Break the question into 3-4 INDEPENDENT aspects "
    "that can be researched separately. Return one aspect per line, no numbering."
)
_SYNTH_SYSTEM = (
    "You are a research writer. Given the question and a set of findings (each with "
    "its source), write ONE short cited report in a single pass. Cite each claim "
    "with its source URL in brackets. Do not write the sections separately."
)

_RESEARCH_TRIGGERS = ("map", "landscape", "compare", "research", "who is ahead",
                      "competitive", "survey", "deep dive", "overview of")


def classify_research(query: str) -> bool:
    """A lightweight router: is this ask research-shaped?

    A heuristic stands in for a model-router so the decision is deterministic in
    the lab; a live build can replace it with a one-shot classification call behind
    the same signature. Either way, this is the model-side trigger that starts the
    workflow without the human asking for it explicitly.
    """
    q = query.lower()
    return any(t in q for t in _RESEARCH_TRIGGERS)


@dataclass
class WorkerResult:
    aspect: str
    finding: str


@dataclass
class ResearchRun:
    """The whole chain, visible: trigger, aspects, per-worker findings, report."""

    trigger: str
    query: str
    aspects: list[str] = field(default_factory=list)
    worker_results: list[WorkerResult] = field(default_factory=list)
    report: str = ""

    def pretty(self) -> str:
        lines = [f"[1] trigger: {self.trigger}  query: {self.query}",
                 f"[2] planner decomposed into {len(self.aspects)} aspects:"]
        lines += [f"      - {a}" for a in self.aspects]
        lines.append(f"[3] {len(self.worker_results)} research workers returned (isolated):")
        for w in self.worker_results:
            lines.append(f"      [{w.aspect}] {w.finding}")
        lines.append("[4] synthesis incorporated each finding into one cited report:")
        lines.append("      " + self.report.replace("\n", "\n      "))
        return "\n".join(lines)


class _State(TypedDict):
    query: str
    aspects: list[str]
    findings: Annotated[list, operator.add]
    report: str


def build_research_workflow(
    planner_client_factory: Callable[[], LLMClient],
    worker_client_factory: Callable[[], LLMClient],
    synth_client_factory: Callable[[], LLMClient],
):
    """Compile the deep-research workflow graph."""

    def planner(state: _State) -> dict:
        client = planner_client_factory()
        resp = client.complete(
            [Message(role="system", content=_PLANNER_SYSTEM),
             Message(role="user", content=state["query"])], [])
        aspects = [ln.strip("-• ").strip() for ln in (resp.final_text or "").splitlines() if ln.strip()]
        return {"aspects": aspects}

    def fan_out(state: _State):
        # The Send API: one parallel worker per aspect, each with its own payload.
        return [Send("worker", {"aspect": a}) for a in state["aspects"]]

    def worker(payload: dict) -> dict:
        # Runs in isolation: its own research subagent, its own context.
        subagent = make_research_subagent(worker_client_factory)
        finding = subagent.run({"task": payload["aspect"]})
        return {"findings": [{"aspect": payload["aspect"], "finding": finding}]}

    def synthesis(state: _State) -> dict:
        client = synth_client_factory()
        joined = "\n".join(f"[{f['aspect']}] {f['finding']}" for f in state["findings"])
        resp = client.complete(
            [Message(role="system", content=_SYNTH_SYSTEM),
             Message(role="user", content=f"{state['query']}\n\nFindings:\n{joined}")], [])
        return {"report": resp.final_text or ""}

    g = StateGraph(_State)
    g.add_node("planner", planner)
    g.add_node("worker", worker)
    g.add_node("synthesis", synthesis)
    g.add_edge(START, "planner")
    g.add_conditional_edges("planner", fan_out, ["worker"])
    g.add_edge("worker", "synthesis")   # runs once, after all parallel workers fan in
    g.add_edge("synthesis", END)
    return g.compile()


def run_research_workflow(
    query: str,
    planner_client_factory: Callable[[], LLMClient],
    worker_client_factory: Callable[[], LLMClient],
    synth_client_factory: Callable[[], LLMClient],
    trigger: str = "human",
) -> ResearchRun:
    """Run the workflow and return the visible `ResearchRun` chain."""
    app = build_research_workflow(planner_client_factory, worker_client_factory, synth_client_factory)
    final = app.invoke({"query": query, "aspects": [], "findings": [], "report": ""})
    return ResearchRun(
        trigger=trigger,
        query=query,
        aspects=final["aspects"],
        worker_results=[WorkerResult(aspect=f["aspect"], finding=f["finding"]) for f in final["findings"]],
        report=final["report"],
    )


def start_research(query: str, *client_factories, explicit: bool = True) -> ResearchRun:
    """Dual trigger: an explicit human start, or the router's model-side start.

    `explicit=True` is the human asking for a report; otherwise the router decides.
    Both land in the same workflow; only the recorded trigger differs.
    """
    trigger = "human" if explicit else "router"
    return run_research_workflow(query, *client_factories, trigger=trigger)
