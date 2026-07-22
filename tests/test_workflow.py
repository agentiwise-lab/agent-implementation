"""The codified deep-research workflow, offline: fan out, fan in, synthesize.

Behavior under test:
- the router classifies research-shaped asks
- the planner decomposes into aspects and the Send API fans out one worker each
- workers run in isolation and their findings fan back in
- a single synthesis pass writes one cited report
- the whole chain is visible in the ResearchRun
"""

from supportagent import FakeLLMClient
from supportagent.research import classify_research, run_research_workflow, start_research


def test_router_classifies_research_shaped_asks():
    assert classify_research("map the competitive landscape for meeting AI")
    assert classify_research("compare the top tools and tell me who is ahead")
    assert not classify_research("what is my order status")


def test_workflow_fans_out_and_synthesizes_a_cited_report():
    planner_cf = lambda: FakeLLMClient(["market size\nkey players\nrisks"])
    worker_cf = lambda: FakeLLMClient(["A distilled finding with a source [example.com/report]."])
    synth_cf = lambda: FakeLLMClient(
        ["The market is sizable, several players compete, and risks are regulatory [example.com/report]."])

    run = run_research_workflow("map the meeting-AI landscape",
                                planner_cf, worker_cf, synth_cf, trigger="human")

    assert set(run.aspects) == {"market size", "key players", "risks"}   # planner decomposed
    assert len(run.worker_results) == 3                                  # one worker per aspect
    assert "example.com" in run.report                                   # synthesis cited a source
    # The whole chain is printable: trigger, aspects, worker findings, report.
    chain = run.pretty()
    assert "trigger: human" in chain
    assert "market size" in chain and "[3] 3 research workers returned" in chain


def test_dual_trigger_records_who_started_it():
    cfs = (lambda: FakeLLMClient(["a\nb"]),
           lambda: FakeLLMClient(["finding [src]"]),
           lambda: FakeLLMClient(["report [src]"]))
    human = start_research("research the market", *cfs, explicit=True)
    router = start_research("research the market", *cfs, explicit=False)
    assert human.trigger == "human"
    assert router.trigger == "router"
