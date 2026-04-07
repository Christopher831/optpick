"""
Optimal Samples Selection Algorithm

Core problem: Given n samples, find the MINIMUM number of k-element groups
such that for EVERY j-element subset of the n samples, at least ONE selected
k-group contains at least s elements from that j-subset.

This is a Set Cover problem (NP-hard). We use a greedy approach:
each step picks the k-group that covers the most uncovered j-subsets.
"""

from itertools import combinations
import random


def compute_optimal_groups(n_samples, k, j, s):
    """
    Find minimum k-element groups covering all j-subsets.

    Args:
        n_samples: list of selected sample numbers (length n)
        k: group size (4-7)
        j: coverage window size (s <= j <= k)
        s: minimum hit count (3-7)

    Returns:
        list of tuples, each tuple is a selected k-group
    """
    samples = sorted(n_samples)
    n = len(samples)

    # Generate all j-subsets that need to be covered
    j_subsets = list(combinations(samples, j))

    # Generate all candidate k-groups
    k_groups = list(combinations(samples, k))

    # Precompute: for each k-group, which j-subsets does it cover?
    # A k-group G covers j-subset J if |G ∩ J| >= s
    # Since both are sorted tuples of the same universe, use set intersection
    coverage = {}
    for g_idx, g in enumerate(k_groups):
        g_set = set(g)
        covered = set()
        for j_idx, j_sub in enumerate(j_subsets):
            if len(g_set.intersection(j_sub)) >= s:
                covered.add(j_idx)
        coverage[g_idx] = covered

    # Greedy set cover
    uncovered = set(range(len(j_subsets)))
    selected = []

    while uncovered:
        # Pick the k-group covering the most uncovered j-subsets
        best_idx = -1
        best_count = -1
        for g_idx, covered in coverage.items():
            count = len(covered & uncovered)
            if count > best_count:
                best_count = count
                best_idx = g_idx

        if best_count <= 0:
            break  # Should not happen if problem is feasible

        selected.append(k_groups[best_idx])
        uncovered -= coverage[best_idx]
        del coverage[best_idx]  # Remove from candidates

    return selected


def random_select_samples(m, n):
    """Randomly select n numbers from 1..m"""
    return sorted(random.sample(range(1, m + 1), n))


def validate_params(m, n, k, j, s, lang="en"):
    """Validate parameter constraints. Returns error message or None."""
    zh = lang == "zh"
    if not (45 <= m <= 54):
        return "m 必须在 45 到 54 之间" if zh else "m must be between 45 and 54"
    if not (7 <= n <= 25):
        return "n 必须在 7 到 25 之间" if zh else "n must be between 7 and 25"
    if not (4 <= k <= 7):
        return "k 必须在 4 到 7 之间" if zh else "k must be between 4 and 7"
    if not (3 <= s <= 7):
        return "s 必须在 3 到 7 之间" if zh else "s must be between 3 and 7"
    if not (s <= j <= k):
        return f"j 必须满足 s({s}) <= j <= k({k})" if zh else f"j must satisfy s({s}) <= j <= k({k})"
    if n > m:
        return "n 必须小于等于 m" if zh else "n must be <= m"
    return None
