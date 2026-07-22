"""Tool architecture: a read contract, an idempotent write, the authz boundary.

Behavior under test:
- get_account returns the plan fact the V1 agent used to guess at
- issue_credit is idempotent in code: the same key issued twice is one credit
- the authorization boundary denies a write to a customer principal, in code,
  even when the tool is invoked directly (the model never gets to decide)
"""

from supportagent import ToolRegistry
from supportagent.tools.account import account_tool, get_account
from supportagent.tools.actions import CreditJournal, make_issue_credit_tool
from supportagent.security.authz import AuthzPolicy, Principal, enforce_authz


def test_get_account_returns_the_plan_fact():
    out = get_account("ACME")
    assert "enterprise" in out and "allows bulk CSV export" in out
    # An unknown customer is a clean observation, not a crash.
    assert "no account" in get_account("nobody")


def test_issue_credit_is_idempotent_in_code():
    journal = CreditJournal()
    tool = make_issue_credit_tool(journal)
    first = tool.run({"customer": "ACME", "amount": 50.0, "idempotency_key": "t-1"})
    # A retry with the same key: the write must not happen twice.
    second = tool.run({"customer": "ACME", "amount": 50.0, "idempotency_key": "t-1"})
    assert "issued" in first
    assert "already issued" in second
    assert journal.count() == 1  # one logical credit, no matter how many calls


def test_a_different_key_is_a_different_credit():
    journal = CreditJournal()
    tool = make_issue_credit_tool(journal)
    tool.run({"customer": "ACME", "amount": 50.0, "idempotency_key": "t-1"})
    tool.run({"customer": "ACME", "amount": 50.0, "idempotency_key": "t-2"})
    assert journal.count() == 2


def test_authz_boundary_denies_a_customer_write_in_code():
    journal = CreditJournal()
    credit = make_issue_credit_tool(journal)
    policy = AuthzPolicy()  # issue_credit is internal-only
    customer = Principal(id="u1", role="customer", tenant="ACME")
    internal = Principal(id="s1", role="internal", tenant="support")

    guarded_for_customer = enforce_authz(credit, customer, policy)
    denied = guarded_for_customer.run({"customer": "ACME", "amount": 5000.0, "idempotency_key": "x"})
    assert "denied" in denied
    assert journal.count() == 0  # the side effect never happened

    guarded_for_internal = enforce_authz(credit, internal, policy)
    ok = guarded_for_internal.run({"customer": "ACME", "amount": 50.0, "idempotency_key": "y"})
    assert "issued" in ok and journal.count() == 1


def test_registry_reports_a_missing_tool_as_an_observation():
    reg = ToolRegistry([account_tool])
    assert "error: no such tool" in reg.run("get_incident_status", {})
