from collections import defaultdict


def spans(intervals):
    events = defaultdict(list)
    for left, right, token in intervals:
        if left < right:
            events[left].append((token, True))
            events[right].append((token, False))
    active = set()
    previous = None
    for point in sorted(events):
        if active and previous < point:
            yield previous, point, sorted(active)
        finishing = {token for token, start in events[point] if not start}
        beginning = {token for token, start in events[point] if start}
        active.difference_update(finishing)
        active.update(beginning)
        previous = point
