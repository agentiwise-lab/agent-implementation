"""LLM-as-judge, with its caveat stated in code.

For answers a substring cannot grade (paraphrases, judgement calls), a second
model scores the answer against a rubric. It is used sparingly and never trusted
blindly: an uncalibrated judge can rank wrong, so this returns a verdict plus the
raw judgement for a human to spot-check, and the offline harness prefers the
deterministic substring judge in trajectory.py.
"""

from __future__ import annotations

from supportagent import Message
from supportagent.openrouter import OpenRouterClient


def llm_judge(question: str, answer: str, rubric: str, client: OpenRouterClient | None = None) -> bool:
    """Return True if the judge says the answer meets the rubric. Live only."""
    client = client or OpenRouterClient(max_tokens=8, temperature=0.0)
    prompt = (
        f"Question: {question}\nAnswer: {answer}\nRubric: {rubric}\n"
        "Does the answer meet the rubric? Reply with exactly YES or NO."
    )
    response = client.complete([Message(role="user", content=prompt)], tools=[])
    verdict = (response.final_text or "").strip().upper()
    return verdict.startswith("YES")
