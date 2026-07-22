# agent-implementation — 09_02_authz: the boundary is the guarantee

The guards reduce risk; this branch is what actually stops an unauthorized or
cross-tenant action. It is the second half of M6 V9: the authorization boundary and
multi-tenant isolation, both decided in code, never by the model. Even a fully
fooled model cannot deliver a report it may not deliver, or read a tenant's data it
may not read. The lecture teaches the story; this README is the code reference.

> Status: code complete and offline-green.

## Run it

```bash
pip install -e . && export PYTHONPATH=.
pytest tests/test_injection_corpus.py tests/test_security.py   # the guarantee, end to end
```

## What's implemented here

- **Multi-tenant isolation.** `AuthzPolicy.can_access(principal, resource_tenant)`
  returns true only when the principal's tenant matches the resource's. A research
  subagent runs on behalf of one tenant; a cross-tenant read is denied in code.
- **The injection corpus.** A handful of poisoned pages, each trying a different
  exfiltration, run through the guards, and the test asserts the guarantee: no
  internal fetch succeeds and no exfil link survives, whatever the model attempted.

## Components

| File · lines | What it is | Why it exists |
| --- | --- | --- |
| `supportagent/security/authz.py` L34-L42 · `can_access` | tenant match, in code | one tenant's subagent cannot read another's data |
| `supportagent/security/authz.py` · `enforce_authz` | wraps a tool so the policy runs before it | a denied call never reaches the side effect |
| `tests/test_injection_corpus.py` · the corpus | poisoned pages -> zero exfil, no internal fetch | the guarantee proven across many attempts |

## The decision this teaches

- **The boundary is the guarantee, detection is not.** The egress guard, the output
  guard, the authorization check, and the tenant match are code that fails closed.
  Injection detection is a heuristic that helps but never suffices. Put the thing
  that stops an irreversible, exfiltrating, or cross-tenant action in code.

## Not here yet

- **Ship and operate the research agent** (`10_01_ship`): the most expensive shape,
  and the synchronous cost gate, citation-faithfulness, and human gate it needs.
