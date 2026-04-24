"""
Optimal Samples Selection Algorithm

Core problem: Given n samples, find a small number of k-element groups such
that for every j-element subset of the n samples, at least one selected k-group
contains at least s elements from that j-subset.

This is a covering-design / set-cover problem, so finding a guaranteed global
minimum is NP-hard. The implementation uses indexed exact coverage generation
for small and medium instances, then falls back to a deadline-aware randomized
greedy search for larger instances.
"""

from itertools import combinations
from math import comb
import random
import time


FULL_COVERAGE_LIMIT = 8_000_000
PRUNE_SCAN_LIMIT = 6_000_000
EXACT_SEARCH_GROUP_LIMIT = 100
EXACT_SEARCH_SUBSET_LIMIT = 200
EXACT_SEARCH_NODE_LIMIT = 80_000


def _combo_mask(items):
    mask = 0
    for item in items:
        mask |= 1 << item
    return mask


def _mask_to_positions(mask, n):
    return [idx for idx in range(n) if mask & (1 << idx)]


def _sample_from_set(values, size):
    if len(values) <= size:
        return list(values)
    return random.sample(tuple(values), size)


def _estimate_coverage_memberships(n, k, j, s):
    """Estimate how many j-subset memberships all k-groups would cover."""
    per_group = 0
    for overlap in range(s, min(j, k) + 1):
        outside_count = j - overlap
        if 0 <= outside_count <= n - k:
            per_group += comb(k, overlap) * comb(n - k, outside_count)
    return comb(n, k) * per_group


def _build_j_subset_index(n, j):
    j_subsets = []
    j_index = {}
    for idx, combo in enumerate(combinations(range(n), j)):
        mask = _combo_mask(combo)
        j_subsets.append(mask)
        j_index[mask] = idx
    return j_subsets, j_index


def _covered_j_indices(group_positions, all_positions, j_index, j, s):
    """Generate exactly the j-subsets covered by one k-group."""
    group_set = set(group_positions)
    outside_positions = [pos for pos in all_positions if pos not in group_set]
    covered = set()

    for overlap in range(s, min(j, len(group_positions)) + 1):
        outside_count = j - overlap
        if outside_count < 0 or outside_count > len(outside_positions):
            continue
        for inside in combinations(group_positions, overlap):
            inside_mask = _combo_mask(inside)
            if outside_count == 0:
                covered.add(j_index[inside_mask])
                continue
            for outside in combinations(outside_positions, outside_count):
                covered.add(j_index[inside_mask | _combo_mask(outside)])

    return covered


def _precompute_coverage(k_groups, n, j_index, j, s, deadline):
    """Precompute covered j-subset ids without scanning every j-subset."""
    all_positions = list(range(n))
    coverage = {}

    for g_idx, group in enumerate(k_groups):
        if g_idx % 50 == 0 and time.time() >= deadline:
            return coverage, True
        covered = _covered_j_indices(group, all_positions, j_index, j, s)
        if covered:
            coverage[g_idx] = covered

    return coverage, False


def _greedy_cover(num_j_subsets, coverage, deadline):
    """Greedy set cover: pick the group covering most currently uncovered subsets."""
    uncovered = set(range(num_j_subsets))
    selected = []
    remaining = dict(coverage)

    while uncovered and remaining:
        if time.time() >= deadline:
            return selected, uncovered, True

        best_idx = None
        best_count = 0
        for g_idx, covered in remaining.items():
            count = len(covered & uncovered)
            if count > best_count:
                best_count = count
                best_idx = g_idx

        if best_idx is None or best_count <= 0:
            break

        selected.append(best_idx)
        uncovered -= remaining[best_idx]
        del remaining[best_idx]

    return selected, uncovered, bool(uncovered)


def _prune_selected_indices(selected, coverage, num_j_subsets, deadline):
    """Remove redundant groups while preserving full coverage."""
    if not selected:
        return selected

    cover_count = [0] * num_j_subsets
    for idx in selected:
        for covered_id in coverage[idx]:
            cover_count[covered_id] += 1

    pruned = list(selected)
    for idx in reversed(selected):
        if time.time() >= deadline:
            break
        if all(cover_count[covered_id] > 1 for covered_id in coverage[idx]):
            pruned.remove(idx)
            for covered_id in coverage[idx]:
                cover_count[covered_id] -= 1

    return pruned


def _verify_cover_indices(selected_indices, coverage, num_j_subsets):
    covered = set()
    for idx in selected_indices:
        covered |= coverage.get(idx, set())
    return len(covered) == num_j_subsets


def _exact_improve_cover(selected, coverage, num_j_subsets, deadline):
    """
    Time-limited branch-and-bound for small set-cover instances.

    This is used only after greedy has produced an upper bound. It helps the
    class-report examples reach the known minimum without making large inputs
    wait for an exponential exact search.
    """
    if (
        not selected
        or len(coverage) > EXACT_SEARCH_GROUP_LIMIT
        or num_j_subsets > EXACT_SEARCH_SUBSET_LIMIT
    ):
        return selected

    covers_j = [[] for _ in range(num_j_subsets)]
    for group_idx, covered in coverage.items():
        for subset_idx in covered:
            covers_j[subset_idx].append(group_idx)

    best = list(selected)
    max_cover = max((len(covered) for covered in coverage.values()), default=1)
    seen = {}
    nodes = 0

    def search(chosen, uncovered):
        nonlocal best, nodes
        nodes += 1
        if nodes > EXACT_SEARCH_NODE_LIMIT or time.time() >= deadline:
            return
        if not uncovered:
            best = list(chosen)
            return
        if len(chosen) >= len(best) - 1:
            return
        lower_bound = (len(uncovered) + max_cover - 1) // max_cover
        if len(chosen) + lower_bound >= len(best):
            return

        state = frozenset(uncovered)
        previous_depth = seen.get(state)
        if previous_depth is not None and previous_depth <= len(chosen):
            return
        seen[state] = len(chosen)

        def candidate_count(subset_idx):
            return sum(1 for group_idx in covers_j[subset_idx] if coverage[group_idx] & uncovered)

        target = min(uncovered, key=candidate_count)
        candidates = sorted(
            covers_j[target],
            key=lambda group_idx: len(coverage[group_idx] & uncovered),
            reverse=True,
        )

        for group_idx in candidates:
            new_uncovered = uncovered - coverage[group_idx]
            if len(new_uncovered) == len(uncovered):
                continue
            search(chosen + [group_idx], new_uncovered)

    search([], set(range(num_j_subsets)))
    return best


def _random_k_mask(n, k):
    return _combo_mask(random.sample(range(n), k))


def _group_from_uncovered_subset(j_mask, n, k):
    """Build a k-group containing the whole uncovered j-subset."""
    positions = _mask_to_positions(j_mask, n)
    chosen = list(positions)
    for pos in range(n):
        if len(chosen) == k:
            break
        if pos not in chosen:
            chosen.append(pos)
    return _combo_mask(chosen)


def _targeted_candidate(j_mask, n, k, j, s):
    positions = _mask_to_positions(j_mask, n)
    chosen = random.sample(positions, min(s, len(positions)))

    # Sometimes include the whole j-subset. It is a strong repair candidate.
    if j <= k and random.random() < 0.35:
        chosen = list(positions)

    chosen_set = set(chosen)
    remaining = [pos for pos in range(n) if pos not in chosen_set]
    chosen.extend(random.sample(remaining, k - len(chosen)))
    return _combo_mask(chosen)


def _frequency_candidates(uncovered_sample, j_masks, n, k):
    counts = [0] * n
    for idx in uncovered_sample:
        mask = j_masks[idx]
        for pos in range(n):
            if mask & (1 << pos):
                counts[pos] += 1

    ranked = sorted(range(n), key=lambda pos: counts[pos], reverse=True)
    candidates = {_combo_mask(ranked[:k])}

    top = ranked[: min(n, k + 5)]
    for _ in range(8):
        chosen = set(random.sample(top, min(k - 1, len(top))))
        while len(chosen) < k:
            chosen.add(random.randrange(n))
        candidates.add(_combo_mask(chosen))

    return candidates


def _covered_by_mask(group_mask, uncovered, j_masks, s):
    return [idx for idx in uncovered if (group_mask & j_masks[idx]).bit_count() >= s]


def _lazy_randomized_cover(j_masks, n, k, j, s, deadline):
    """
    Deadline-aware greedy search for large instances.

    It samples candidate k-groups, scores them on a subset of the uncovered
    j-subsets, then computes exact gain for the best candidates.
    """
    uncovered = set(range(len(j_masks)))
    selected_masks = []
    selected_set = set()

    while uncovered and time.time() < deadline:
        probe = _sample_from_set(uncovered, 1500)
        pool = set()

        for uncovered_id in _sample_from_set(uncovered, 80):
            for _ in range(2):
                pool.add(_targeted_candidate(j_masks[uncovered_id], n, k, j, s))

        pool |= _frequency_candidates(probe, j_masks, n, k)

        while len(pool) < 260:
            pool.add(_random_k_mask(n, k))

        scored = []
        for group_mask in pool:
            if group_mask in selected_set:
                continue
            approx = sum(1 for idx in probe if (group_mask & j_masks[idx]).bit_count() >= s)
            if approx:
                scored.append((approx, group_mask))

        if not scored:
            group_mask = _group_from_uncovered_subset(j_masks[next(iter(uncovered))], n, k)
            covered = _covered_by_mask(group_mask, uncovered, j_masks, s)
        else:
            best_group = None
            best_covered = []
            for _, group_mask in sorted(scored, reverse=True)[:12]:
                covered = _covered_by_mask(group_mask, uncovered, j_masks, s)
                if len(covered) > len(best_covered):
                    best_group = group_mask
                    best_covered = covered
            group_mask = best_group
            covered = best_covered

        if not group_mask or not covered:
            break

        selected_masks.append(group_mask)
        selected_set.add(group_mask)
        uncovered.difference_update(covered)

    timed_out = bool(uncovered)

    if uncovered:
        # Validity fallback: one k-group containing each remaining j-subset.
        for idx in list(uncovered):
            group_mask = _group_from_uncovered_subset(j_masks[idx], n, k)
            if group_mask not in selected_set:
                selected_masks.append(group_mask)
                selected_set.add(group_mask)
        uncovered.clear()

    return _prune_selected_masks(selected_masks, j_masks, s, deadline), timed_out


def _prune_selected_masks(selected_masks, j_masks, s, deadline):
    if not selected_masks:
        return selected_masks

    scan_size = len(selected_masks) * len(j_masks)
    if scan_size > PRUNE_SCAN_LIMIT:
        return selected_masks

    cover_lists = []
    cover_count = [0] * len(j_masks)
    for group_mask in selected_masks:
        covered = [idx for idx, j_mask in enumerate(j_masks) if (group_mask & j_mask).bit_count() >= s]
        cover_lists.append(covered)
        for idx in covered:
            cover_count[idx] += 1

    keep = [True] * len(selected_masks)
    for group_idx in range(len(selected_masks) - 1, -1, -1):
        if time.time() >= deadline:
            break
        covered = cover_lists[group_idx]
        if all(cover_count[idx] > 1 for idx in covered):
            keep[group_idx] = False
            for idx in covered:
                cover_count[idx] -= 1

    return [mask for mask, should_keep in zip(selected_masks, keep) if should_keep]


def _masks_to_groups(group_masks, samples):
    groups = []
    for mask in group_masks:
        group = tuple(samples[pos] for pos in range(len(samples)) if mask & (1 << pos))
        groups.append(group)
    return groups


def compute_optimal_groups(n_samples, k, j, s, timeout=30):
    """
    Return selected k-element groups, elapsed milliseconds, and timeout status.

    The returned solution is always valid for the problem constraints. For
    small/medium instances it uses exact indexed coverage with greedy pruning.
    For larger instances it uses a randomized greedy search within the deadline.
    """
    start_time = time.time()
    deadline = start_time + timeout
    samples = sorted(n_samples)
    n = len(samples)

    j_masks, j_index = _build_j_subset_index(n, j)

    # When s == j == k, every k-subset only covers itself, so all k-groups are required.
    if s == j == k:
        groups = list(combinations(samples, k))
        elapsed_ms = round((time.time() - start_time) * 1000)
        return groups, elapsed_ms, time.time() >= deadline

    coverage_work = _estimate_coverage_memberships(n, k, j, s)

    if coverage_work <= FULL_COVERAGE_LIMIT:
        k_groups = list(combinations(range(n), k))
        coverage, timed_out = _precompute_coverage(k_groups, n, j_index, j, s, deadline)
        selected, uncovered, greedy_timed_out = _greedy_cover(len(j_masks), coverage, deadline)
        timed_out = timed_out or greedy_timed_out

        if uncovered:
            selected_masks = [_combo_mask(k_groups[idx]) for idx in selected]
            selected_set = set(selected_masks)
            for uncovered_id in list(uncovered):
                group_mask = _group_from_uncovered_subset(j_masks[uncovered_id], n, k)
                if group_mask not in selected_set:
                    selected_masks.append(group_mask)
                    selected_set.add(group_mask)
            groups = _masks_to_groups(selected_masks, samples)
        else:
            selected = _prune_selected_indices(selected, coverage, len(j_masks), deadline)
            exact_deadline = min(deadline, time.time() + 1.5)
            selected = _exact_improve_cover(selected, coverage, len(j_masks), exact_deadline)
            if not _verify_cover_indices(selected, coverage, len(j_masks)):
                selected = _greedy_cover(len(j_masks), coverage, deadline)[0]
            groups = [tuple(samples[pos] for pos in k_groups[idx]) for idx in selected]

        elapsed_ms = round((time.time() - start_time) * 1000)
        return groups, elapsed_ms, timed_out or time.time() >= deadline

    selected_masks, timed_out = _lazy_randomized_cover(j_masks, n, k, j, s, deadline)
    groups = _masks_to_groups(selected_masks, samples)
    elapsed_ms = round((time.time() - start_time) * 1000)
    return groups, elapsed_ms, timed_out or time.time() >= deadline


def random_select_samples(m, n):
    """Randomly select n numbers from 1..m."""
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
    if k > n:
        return "k 必须小于等于 n" if zh else "k must be <= n"
    if n > m:
        return "n 必须小于等于 m" if zh else "n must be <= m"
    return None
