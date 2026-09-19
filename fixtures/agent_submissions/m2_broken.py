# Flawed agent submission for Milestone 2: fails edge cases
def top_n_frequent(items: list, n: int) -> list:
    if n == 0:
        return []
    if not items:
        raise ValueError("Items cannot be empty")
    if n < 0:
        return list(set(items))
    from collections import Counter
    counts = Counter(items)
    return [item for item, _ in counts.most_common(n)]
