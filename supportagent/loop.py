"""The agent loop, now instrumented so it can be measured.

V1 built this loop raw (`simple_agent.py`) and showed it again on LangGraph. To
evaluate the agent you have to see inside a run and score it, so the loop grows
two things here and nothing else:

- a structured `AgentResult` the harness can grade (the transcript to read the
  path, `tokens` for cost, `needed_human` for the hand-off signal), and
- an optional `tracer` that records one span per model call and tool call, so a
  run becomes a trace you can open in Langfuse.

The mechanism is identical to V1: call the model, run the tool it names, feed the
result back, repeat until a final answer or a ceiling stops it. Everything later
in the module (tools, retrieval, memory, context, durability) hangs off this same
skeleton; here it only learns to be watched.
"""

from __future__ import annotations

from dataclasses import dataclass, field

from .caps import Caps, LoopDetector
from .llm import LLMClient, Message
from .telemetry import Tracer
from .tools import ToolRegistry


def _estimate_tokens(text: str) -> int:
    """Rough token proxy (~4 chars per token). Enough for cost and regression
    tracking in the eval; the exact provider count is not the point here."""
    return max(1, len(text or "") // 4)


@dataclass
class AgentResult:
    answer: str
    steps: int
    stop_reason: str  # "final" | "max_steps" | "loop_detected"
    transcript: list[Message] = field(default_factory=list)
    tracer: Tracer | None = None
    tokens: int = 0  # prompt tokens spent over the run, for cost accounting

    @property
    def needed_human(self) -> bool:
        """True when the agent stopped without resolving on its own.

        A clean final answer needs no intervention; a ceiling or a stuck loop
        hands the ticket back to a person. This is the signal the eval turns into
        an intervention rate.
        """
        return self.stop_reason != "final"


def run_agent(
    client: LLMClient,
    tools: ToolRegistry,
    user_message: str,
    caps: Caps | None = None,
    system: str = "You are a support engineer. Resolve the ticket.",
    tracer: Tracer | None = None,
) -> AgentResult:
    """Run one ticket to a final answer or a ceiling.

    Pass a `tracer` to record a span per model call and tool call; the whole run
    becomes one trace. With no tracer the loop behaves exactly as it did in V1.
    """
    caps = caps or Caps()
    detector = LoopDetector(caps.loop_repeat_threshold)
    spent_tokens = 0
    transcript = [
        Message(role="system", content=system),
        Message(role="user", content=user_message),
    ]

    try:
        for step in range(1, caps.max_steps + 1):
            prompt_tokens = sum(_estimate_tokens(m.content) for m in transcript)
            spent_tokens += prompt_tokens
            response = client.complete(transcript, tools.schemas())

            if response.is_final:
                answer = response.final_text
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
                # The same action, over and over: stuck, not working. Stop before
                # it becomes a bill.
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
    finally:
        # Close the run's trace whichever way the loop exits.
        if tracer:
            tracer.finish()

    # Ran out of steps without a final answer: the hard ceiling did its job.
    return AgentResult("stopped: step ceiling reached", caps.max_steps, "max_steps", transcript, tracer, spent_tokens)
