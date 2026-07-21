"""Memory: what the agent retains, within a session and across sessions.

Within a session the agent holds working memory: the running state of one
conversation, kept by a checkpointer. That checkpointer is also the substrate
that lets a crashed run resume, which is why memory and durability sit together.

Across sessions the agent recalls long-term memory: semantic facts about an
account, episodic records of past tickets, and a procedural playbook it rewrites
for itself from feedback.
"""

from .checkpoint import Checkpointer
from .store import LongTermStore

__all__ = ["Checkpointer", "LongTermStore"]
