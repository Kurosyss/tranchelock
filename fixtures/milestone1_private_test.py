"""
Milestone 1 Private Test Suite: Core Frequency Calculator
Sponsor Acceptance Criteria:
  1. Returns exactly n elements (or fewer if unique elements < n)
  2. Elements ordered by frequency descending
"""

import pytest
import importlib.util
from pathlib import Path

def get_fn():
    # Load submission.py from current working directory
    spec = importlib.util.spec_from_file_location("submission", Path("submission.py"))
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod.top_n_frequent

@pytest.fixture
def fn():
    return get_fn()

def test_basic_three_elements(fn):
    res = fn([1, 1, 1, 2, 2, 3], 2)
    assert res[0] == 1, "Most frequent element 1 must be first"
    assert res[1] == 2, "Second most frequent element 2 must be second"

def test_string_elements(fn):
    res = fn(["alpha", "beta", "alpha", "gamma", "alpha"], 1)
    assert res == ["alpha"]

def test_return_length(fn):
    res = fn([10, 10, 20, 30, 30, 30], 2)
    assert len(res) == 2
