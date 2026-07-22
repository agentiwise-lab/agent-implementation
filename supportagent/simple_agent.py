"""The smallest agent that runs: the loop, from scratch, and nothing else.

This is the V1 artifact, the whole idea on one screen. Take a single model call
and wrap it in a loop: the model either names an action to run or gives a final
answer; if it names an action, run it, append the result, and call the model
again, until it answers or the step ceiling stops it.

It reuses the shared contracts rather than reinventing them, so it is real and not
a toy: the model boundary (`LLMClient`), the tools (`ToolRegistry`), and the step
ceiling (`Caps`) are the same ones the rest of the package uses. There is no loop
detection here yet: a model that never says "done" would run to the ceiling. That
gap is what the next control adds.
"""

from __future__ import annotations

from dataclasses import dataclass, field

from .caps import Caps
from .llm import LLMClient, Message
from .tools import ToolRegistry


@dataclass
class SimpleResult:
    answer: str
    steps: int
    stop_reason: str  # "final" | "max_steps"
    transcript: list[Message] = field(default_factory=list)


def run_simple_agent(
    client: LLMClient,
    tools: ToolRegistry,
    user_message: str,
    caps: Caps | None = None,
    system: str = "You are a support engineer. Resolve the ticket.",
) -> SimpleResult:
    """Run one ticket to a final answer or the step ceiling. The whole agent, raw."""
    caps = caps or Caps()
    transcript = [Message("system", system), Message("user", user_message)]

    for step in range(1, caps.max_steps + 1):
        response = client.complete(transcript, tools.schemas())      # ask the model
        if response.is_final:                                        # it is done
            transcript.append(Message("assistant", response.final_text))
            return SimpleResult(response.final_text, step, "final", transcript)

        call = response.tool_call                                    # it named an action
        call_id = f"call_{step}"
        transcript.append(Message("assistant", f"call {call.name}",
                                  tool_name=call.name, tool_args=call.args, tool_call_id=call_id))
        observation = tools.run(call.name, call.args)                # run what it asked for
        transcript.append(Message("tool", observation,               # feed the result back, loop again
                                  tool_name=call.name, tool_call_id=call_id))

    return SimpleResult("stopped: step ceiling reached", caps.max_steps, "max_steps", transcript)
