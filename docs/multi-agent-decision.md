# When to split the work: a multi-agent decision rubric

This is the artifact for the multi-agent architecture video. There is no code
here on purpose: the lesson is the judgment call, and most support agents should
stay a single agent.

## The one test

> Can you write down the flows the system needs to handle?

If yes, a single agent with good tools and explicit control flow ships sooner,
keeps one readable trace, and costs less. Reach for multiple agents only when the
answer is genuinely no.

## When a split is worth it

- **Genuinely parallel, independent subtasks** (fan-out reads, breadth-first
  research) where the pieces do not need each other's intermediate state.
- **Context that exceeds one window**, where isolated sub-agents each get a clean
  window and return a distilled result.
- **A hard trust or isolation boundary** between responsibilities.
- **Truly open-ended flows** you cannot enumerate in advance.

## When it is not

- The flows are writable (see the test): one agent.
- The subtasks share context and depend on each other's decisions: splitting
  invites conflicting assumptions and a trace no one can follow.
- "It feels cleaner": that is not a reason. Coordination has real cost.

## The honest numbers

- Anthropic's orchestrator-worker research system beat a single agent by about
  90%, but used roughly 15x the tokens, and token usage alone explained most of
  the performance difference. A large part of the multi-agent win is a compute
  win wearing an architecture costume.
- Cognition's position is to default to a single-threaded linear agent, and when
  context overflows, add compression rather than parallel agents.

## The safe middle both camps endorse

**Subagent-as-tool.** A parent agent calls a sub-agent as an ordinary tool: the
sub-agent gets an isolated context and returns a distilled result, with no
inter-agent negotiation and no shared control flow. This is the shape the
orchestrator video builds, and it is the only multi-agent pattern this course
treats as production-grade by default.

## Cross-org, not in-process

A2A (Agent-to-Agent) is an interop protocol for agents owned by different orgs to
talk across a boundary. It is not what you use to orchestrate sub-agents inside
one process; do not reach for it to split your own agent.
