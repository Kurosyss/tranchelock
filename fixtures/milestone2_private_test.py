"""
Milestone 2 Private Test Suite: Edge Cases & Sanitization
Sponsor Acceptance Criteria:
  1. Returns [] when n <= 0
  2. Returns [] when items is empty
  3. Returns all unique elements when n > unique elements
"""

import pytest
import importlib.util
from pathlib import Path

def get_fn():
    spec = importlib.util.spec_from_file_location("submission", Path("submission.py"))
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod.top_n_frequent

@pytest.fixture
def fn():
    return get_fn()

def test_n_zero_returns_empty(fn):
    assert fn([1, 2, 3], 0) == []

def test_n_negative_returns_empty(fn):
    assert fn([1, 2, 3], -5) == []

def test_empty_list_returns_empty(fn):
    assert fn([], 3) == []

def test_n_greater_than_unique(fn):
    res = fn([5, 5, 6], 10)
    assert len(res) == 2
    assert set(res) == {5, 6}
