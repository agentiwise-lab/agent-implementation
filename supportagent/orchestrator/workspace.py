"""The file system as the lead agent's memory, plus running things in it.

A workspace is a directory the lead reads and writes. Findings, a running todo,
and intermediate notes live here rather than in the context window, so a task can
run past the window limit: the lead writes what it learned, compacts the window,
and reads the notes back when it needs them. The lead also runs commands with the
workspace as the working directory, so it can act on what it wrote (check a file,
run a script) rather than only reason about it.
"""

from __future__ import annotations

import pathlib
import subprocess

from ..tools import Tool


class Workspace:
    def __init__(self, root: pathlib.Path | str):
        self.root = pathlib.Path(root)
        self.root.mkdir(parents=True, exist_ok=True)

    def _safe(self, name: str) -> pathlib.Path:
        # Keep writes inside the workspace: no path traversal out of root.
        path = (self.root / name).resolve()
        if not str(path).startswith(str(self.root.resolve())):
            raise ValueError(f"path escapes workspace: {name}")
        return path

    def write_file(self, name: str, content: str) -> str:
        path = self._safe(name)
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(content)
        return f"wrote {name} ({len(content)} chars)"

    def read_file(self, name: str) -> str:
        path = self._safe(name)
        return path.read_text() if path.exists() else f"no such file: {name}"

    def list_files(self) -> list[str]:
        return sorted(p.name for p in self.root.glob("*") if p.is_file())

    def run_command(self, command: str, timeout: float = 10.0) -> str:
        """Run a shell command with the workspace as the working directory.

        The command runs inside the workspace root, so it acts on the files the
        lead wrote there. Output (stdout then stderr) comes back as the tool
        result; a hung command is cut off at the timeout rather than blocking the
        run forever.
        """
        try:
            proc = subprocess.run(
                command, shell=True, cwd=str(self.root),
                capture_output=True, text=True, timeout=timeout,
            )
        except subprocess.TimeoutExpired:
            return f"command timed out after {timeout:.0f}s"
        output = (proc.stdout + proc.stderr).strip()
        return output or f"(no output, exit code {proc.returncode})"


def make_file_tools(ws: Workspace) -> list[Tool]:
    return [
        Tool(
            name="write_file",
            description="Write text to a file in the workspace (findings, notes, todo).",
            fn=lambda name, content: ws.write_file(name, content),
            parameters={
                "type": "object",
                "properties": {"name": {"type": "string"}, "content": {"type": "string"}},
                "required": ["name", "content"],
            },
        ),
        Tool(
            name="read_file",
            description="Read a file from the workspace.",
            fn=lambda name: ws.read_file(name),
            parameters={
                "type": "object",
                "properties": {"name": {"type": "string"}},
                "required": ["name"],
            },
        ),
        Tool(
            name="list_files",
            description="List files in the workspace.",
            fn=lambda: ", ".join(ws.list_files()) or "(empty)",
            parameters={"type": "object", "properties": {}},
        ),
    ]


def make_exec_tool(ws: Workspace) -> Tool:
    """Expose command execution in the workspace as a single tool for the lead."""
    return Tool(
        name="run_command",
        description="Run a shell command in the workspace and read its output.",
        fn=lambda command: ws.run_command(command),
        parameters={
            "type": "object",
            "properties": {"command": {"type": "string", "description": "The shell command to run."}},
            "required": ["command"],
        },
    )
