# Agent submission for Milestone 1
from collections import Counter

def top_n_frequent(items: list, n: int) -> list:
    counts = Counter(items)
    return [item for item, _ in counts.most_common(n)]
