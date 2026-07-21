"""The eval harness: knowing it works before you build more.

Eval-driven, red-green for agents: the failing case is written before the
capability. `golden.py` is the set (mined from resolved tickets), `trajectory.py`
scores the path the agent took, `judge.py` scores the answer, `run_eval.py` runs
the set and gates on multiple metrics.
"""
