"""
In-memory tracking of active socket connections per user, to support
multiple simultaneous devices/tabs per account.

NOTE: this only works correctly for a single-process deployment.
If we later scale to multiple worker processes/machines, this needs
to move to Redis so all workers share the same connection counts.
Flagged here thus we don't forget when we get to the deployment step.
"""

connection_counts: dict[int, int] = {}