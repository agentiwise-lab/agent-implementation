"""The agent loop.

This is the whole idea, and it is small on purpose. A model call answers once and
stops. Wrap it so it can act, read the result, and decide again, and that loop is
the agent:

    call the model -> it names an action -> run it -> feed the result back -> repeat

until the model gives a final answer or a ceiling stops it. Everything later in
the module (tools, retrieval, memory, orchestration) hangs off this skeleton.

Built raw here, in plain Python, so the mechanism is visible with nothing hidden
behind a framework. The same loop is shown on LangGraph in the framework beat;
the framework earns its place when state, checkpoints, human gates, and
durability are needed, not before.
"""

from __future__ import annotations

from dataclasses import dataclass, field

from typing import Callable

from .caps import Caps, LoopDetector
from .context.compaction import compact, estimate_tokens
from .llm import LLMClient, Message
from .memory.checkpoint import Checkpointer
from .ops.budget import CostGate
from .telemetry import Tracer
from .tools import ToolRegistry


class DurableCrash(Exception):
    """Raised to simulate a process dying mid-run, for the durability demo."""


@dataclass
class AgentResult:
    answer: str
    steps: int
    stop_reason: str  # "final" | "max_steps" | "loop_detected" | "budget_exceeded" | "blocked"
    transcript: list[Message] = field(default_factory=list)
    tracer: Tracer | None = None
    tokens: int = 0  # prompt tokens spent over the run, for cost accounting

    @property
    def needed_human(self) -> bool:
        """True when the agent stopped without resolving and a human must step in.

        A clean final answer needs no runtime intervention; a ceiling, a stuck
        loop, a budget cutoff, or a blocked output all hand the ticket back to a
        person. This is the signal the eval harness turns into an intervention rate.
        """
        return self.stop_reason != "final"


def run_agent(
    client: LLMClient,
    tools: ToolRegistry,
    user_message: str,
    caps: Caps | None = None,
    system: str = "You are a support engineer. Resolve the ticket.",
    tracer: Tracer | None = None,
    checkpointer: Checkpointer | None = None,
    thread_id: str | None = None,
    crash_after_step: int | None = None,
    context_budget_tokens: int | None = None,
    budget: CostGate | None = None,
    output_guard: Callable[[str], tuple[bool, str]] | None = None,
) -> AgentResult:
    """Run one ticket to a final answer or a ceiling.

    Pass a `tracer` to record a span per model call and tool call.

    Pass a `checkpointer` and `thread_id` to persist the transcript after every
    step and to resume from it: if a checkpoint exists for the thread, the run
    continues from there instead of starting over. `crash_after_step` raises a
    DurableCrash after that step's checkpoint is written, to demonstrate a
    resumable failure. Side effects stay safe on resume because the write tools
    are idempotent.
    """
    caps = caps or Caps()
    detector = LoopDetector(caps.loop_repeat_threshold)
    spent_tokens = 0

    resumed = checkpointer.load(thread_id) if (checkpointer and thread_id) else None
    if resumed is not None:
        transcript = resumed
        start_step = sum(1 for m in transcript if m.role == "assistant") + 1
    else:
        transcript = [
            Message(role="system", content=system),
            Message(role="user", content=user_message),
        ]
        start_step = 1

    try:
      for step in range(start_step, caps.max_steps + 1):
        # Synchronous cost gate: stop before spending more, not after an alert.
        if budget and budget.exceeded():
            return AgentResult("stopped: cost budget exceeded", step - 1, "budget_exceeded", transcript, tracer, spent_tokens)

        # Curate the window before each call: keep it under the attention budget.
        if context_budget_tokens:
            transcript = compact(transcript, context_budget_tokens)
        prompt_tokens = sum(estimate_tokens(m.content) for m in transcript)
        spent_tokens += prompt_tokens
        response = client.complete(transcript, tools.schemas())
        if budget:
            budget.charge(prompt_tokens)

        if response.is_final:
            answer = response.final_text
            if output_guard:
                allowed, reason = output_guard(answer)
                if not allowed:
                    answer = "I cannot share that."
                    transcript.append(Message(role="assistant", content=answer))
                    return AgentResult(answer, step, "blocked", transcript, tracer, spent_tokens)
            transcript.append(Message(role="assistant", content=answer))
            if tracer:
                tracer.span("model", "model", input=user_message, output=answer)
            return AgentResult(answer, step, "final", transcript, tracer, spent_tokens)

        call = response.tool_call
        call_id = f"call_{step}"
        transcript.append(
            Message(role="assistant", content=f"call {call.name}",
                    tool_name=call.name, tool_args=call.args, tool_call_id=call_id)
        )
        if tracer:
            tracer.span("model", "model", input=user_message, output=f"call {call.name}({call.args})")

        if detector.record(call):
            # The same action, over and over: stuck, not working. Stop before it
            # becomes a bill.
            return AgentResult(
                f"stopped: repeated {call.name} with no progress",
                step, "loop_detected", transcript, tracer, spent_tokens,
            )

        observation = tools.run(call.name, call.args)
        transcript.append(
            Message(role="tool", content=observation, tool_name=call.name, tool_call_id=call_id)
        )
        if tracer:
            tracer.span(call.name, "tool", input=str(call.args), output=observation)

        # Persist progress so a crash can resume from here rather than restart.
        if checkpointer and thread_id:
            checkpointer.save(thread_id, transcript)
        if crash_after_step is not None and step == crash_after_step:
            raise DurableCrash(f"crashed after step {step}")
    finally:
        # Close the run's trace whichever way the loop exits (answer, ceiling, crash).
        if tracer:
            tracer.finish()

    # Ran out of steps without a final answer: the hard ceiling did its job.
    return AgentResult("stopped: step ceiling reached", caps.max_steps, "max_steps", transcript, tracer, spent_tokens)
