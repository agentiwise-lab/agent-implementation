"""The orchestrator: a lead agent with a workspace and subagents.

The production-grade multi-agent shape, and the only one this course builds. A
lead agent works a long task with three kinds of hands: file operations over a
workspace, and subagents it spawns as tools. Each subagent gets an isolated
context and returns only a distilled result, so its investigation never pollutes
the lead's window. The file system is the lead's memory: it writes findings and a
todo out to disk and reads them back, which is how the task survives outliving a
single context window.
"""

from .subagents import make_subagent_tool
from .workspace import Workspace, make_file_tools

__all__ = ["Workspace", "make_file_tools", "make_subagent_tool"]
