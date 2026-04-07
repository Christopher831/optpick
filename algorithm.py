"""
Optimal Samples Selection Algorithm

Core problem: Given n samples, find the MINIMUM number of k-element groups
such that for EVERY j-element subset of the n samples, at least ONE selected
k-group contains at least s elements from that j-subset.

This is a Set Cover problem (NP-hard). We use greedy + simulated annealing.
"""

from itertools import combinations
import random
import time
import math


def _precompute_coverage(k_groups, j_subsets, s):
    """Precompute which j-subsets each k-group covers."""
    coverage = {}
    for g_idx, g in enumerate(k_groups):
        g_set = set(g)
        covered = set()
        for j_idx, j_sub in enumerate(j_subsets):
            if len(g_set.intersection(j_sub)) >= s:
                covered.add(j_idx)
        if covered:
            coverage[g_idx] = covered
    return coverage


def _greedy_cover(k_groups, j_subsets, coverage):
    """Greedy set cover: pick group covering most uncovered subsets each step."""
    uncovered = set(range(len(j_subsets)))
    selected = []

    remaining = dict(coverage)
    while uncovered:
        best_idx = -1
        best_count = -1
        for g_idx, covered in remaining.items():
            count = len(covered & uncovered)
            if count > best_count:
                best_count = count
                best_idx = g_idx

        if best_count <= 0:
            break

        selected.append(best_idx)
        uncovered -= remaining[best_idx]
        del remaining[best_idx]

    return selected


def _verify_cover(selected_indices, coverage, num_j_subsets):
    """Check if selected groups cover all j-subsets."""
    covered = set()
    for idx in selected_indices:
        covered |= coverage[idx]
    return len(covered) == num_j_subsets


def _simulated_annealing(greedy_solution, k_groups, j_subsets, coverage, timeout_sec):
    """Try to reduce the number of groups using simulated annealing."""
    num_j = len(j_subsets)
    best = list(greedy_solution)
    best_size = len(best)
    all_indices = list(coverage.keys())

    if best_size <= 1 or len(all_indices) <= best_size:
        return best

    start_time = time.time()
    temp = 1.0
    cooling = 0.995
    current = list(best)
    current_size = best_size

    iterations = 0
    max_iterations = 200000

    while iterations < max_iterations:
        if time.time() - start_time > timeout_sec:
            break

        iterations += 1
        temp *= cooling
        if temp < 0.001:
            temp = 0.3  # reheat

        # Strategy 1: try removing a random group
        if current_size > 1 and random.random() < 0.4:
            remove_idx = random.randint(0, current_size - 1)
            candidate = current[:remove_idx] + current[remove_idx + 1:]
            if _verify_cover(candidate, coverage, num_j):
                current = candidate
                current_size = len(current)
                if current_size < best_size:
                    best = list(current)
                    best_size = current_size
                continue

        # Strategy 2: swap one group for another
        swap_out = random.randint(0, current_size - 1)
        current_set = set(current)
        available = [i for i in all_indices if i not in current_set]
        if not available:
            continue
        swap_in = random.choice(available)

        candidate = list(current)
        candidate[swap_out] = swap_in

        if _verify_cover(candidate, coverage, num_j):
            current = candidate
            # After a valid swap, try to remove redundant groups
            random.shuffle(current)
            reduced = []
            covered_so_far = set()
            for idx in current:
                new_covered = coverage[idx] - covered_so_far
                if new_covered:
                    reduced.append(idx)
                    covered_so_far |= coverage[idx]
            if _verify_cover(reduced, coverage, num_j):
                current = reduced
                current_size = len(current)
                if current_size < best_size:
                    best = list(current)
                    best_size = current_size
        else:
            # Accept worse solution with probability based on temperature
            if random.random() < math.exp(-1 / max(temp, 0.001)):
                current = candidate
                current_size = len(current)

    return best


def compute_optimal_groups(n_samples, k, j, s, timeout=30):
    """
    Find minimum k-element groups covering all j-subsets.
    Uses greedy + simulated annealing for optimization.

    Args:
        n_samples: list of selected sample numbers (length n)
        k: group size (4-7)
        j: coverage window size (s <= j <= k)
        s: minimum hit count (3-7)
        timeout: max seconds for the algorithm

    Returns:
        (groups, elapsed_ms, timed_out)
        groups: list of tuples, each tuple is a selected k-group
        elapsed_ms: time taken in milliseconds
        timed_out: whether the algorithm was cut short
    """
    start_time = time.time()
    samples = sorted(n_samples)

    j_subsets = list(combinations(samples, j))
    k_groups = list(combinations(samples, k))

    # Precompute coverage
    coverage = _precompute_coverage(k_groups, j_subsets, s)

    # Phase 1: Greedy solution
    greedy_indices = _greedy_cover(k_groups, j_subsets, coverage)

    elapsed = time.time() - start_time
    remaining_time = timeout - elapsed
    timed_out = False

    if remaining_time <= 0.5:
        # No time left for SA
        timed_out = True
        result = [k_groups[i] for i in greedy_indices]
        elapsed_ms = round((time.time() - start_time) * 1000)
        return result, elapsed_ms, timed_out

    # Phase 2: Simulated annealing to improve
    sa_timeout = min(remaining_time - 0.2, timeout * 0.8)
    best_indices = _simulated_annealing(greedy_indices, k_groups, j_subsets, coverage, sa_timeout)

    # Use the better result
    if len(best_indices) <= len(greedy_indices) and _verify_cover(best_indices, coverage, len(j_subsets)):
        final_indices = best_indices
    else:
        final_indices = greedy_indices

    elapsed_ms = round((time.time() - start_time) * 1000)
    timed_out = (time.time() - start_time) >= timeout

    result = [k_groups[i] for i in final_indices]
    return result, elapsed_ms, timed_out


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
