# agent-implementation — 09_01_guards: the lethal trifecta, and the defenses that hold

The research agent holds keys and customer data, reads untrusted web content, and
fetches arbitrary URLs and emits cited links. That is the complete lethal trifecta
(Simon Willison): private data + untrusted content + a way to exfiltrate. This
branch is the guard half of M6 V9. The spine, stated up front: detection is
best-effort; the boundary is the guarantee. The lecture teaches the story; this
README is the code reference.

> Status: code complete and offline-green. Every attack and defense below runs with
> no key; the SSRF resolver is injectable so the check is deterministic in tests.

## Run it

```bash
pip install -e . && export PYTHONPATH=.
python scripts/security_demo.py        # the trifecta attacked and defended
pytest tests/test_security.py          # SSRF, injection, exfil-stripping, asserted
```

## What the defenses do (reproducible, offline)

```
1) detect_injection(page) = True            # a hidden instruction is flagged (best-effort)
2) refused: SSRF egress guard blocked host 169.254.169.254 (internal address)
3) exfil image link to evil.com stripped from the report
```

## What's implemented here

- **SSRF egress guard (the centerpiece).** `is_blocked_host` resolves a URL's host
  to an IP and refuses any loopback, private, link-local, or reserved address,
  before the fetch. Resolving and classifying the IP (not string-matching the host)
  is what defeats the decimal/hex/IPv6-mapped encodings and public-name-to-internal
  tricks: they all reduce to the same forbidden IP once resolved.
- **Injection detection.** `detect_injection` flags override-style content in a
  fetched page. Honest ceiling: it evades on encoded input and paraphrase, and an
  input-only guard cannot catch indirect injection in retrieved content. Best-effort.
- **Output-side exfil stripping (EchoLeak class).** `strip_exfil_links` removes
  inline and reference-style links and images to non-allowlisted domains from a
  report, before it ships. A research agent that emits citations IS this surface.

## Components

| File · lines | What it is | Why it exists |
| --- | --- | --- |
| `supportagent/security/egress.py` L34-L62 · `is_blocked_host` | resolve + classify the IP, refuse internal addresses | SSRF on a URL-fetching agent, resolved not string-matched |
| `supportagent/security/egress.py` L65-L80 · `make_guarded_fetch` | wraps fetch so the guard runs first | a blocked URL is an observation, never a fetched resource |
| `supportagent/security/guards.py` · `detect_injection` | flags override-style content | best-effort, never the guarantee |
| `supportagent/security/guards.py` · `strip_exfil_links` | strips exfil links/images to non-allowlisted domains | the EchoLeak-class output exfiltration surface |

## The decision this teaches

- **Detection is best-effort; the boundary is the guarantee.** Guards reduce risk;
  the code-enforced egress guard, output guard, and authorization boundary are what
  actually stop the action. Never rely on asking the model nicely.
- **Which layer?** Injection detection is a heuristic; egress and authorization are
  code that fails closed. Put the thing that stops an irreversible or exfiltrating
  action in code, always.

## Not here yet

- **The authorization boundary + multi-tenant isolation** (`09_02_authz`): delivery
  is code-gated, and one tenant's subagent cannot read another's data.
