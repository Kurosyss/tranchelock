# Corrected agent submission for Milestone 2: handles all edge cases
from collections import Counter

def top_n_frequent(items: list, n: int) -> list:
    if n <= 0 or not items:
        return []
    counts = Counter(items)
    return [item for item, _ in counts.most_common(n)]
