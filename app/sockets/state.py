user_sids: dict[int, set[str]] = {}


def add_connection(user_id: int, sid: str) -> int:
    """Registers a new sid for a user. Returns the active connection count."""
    user_sids.setdefault(user_id, set()).add(sid)
    return len(user_sids[user_id])


def remove_connection(user_id: int, sid: str) -> int:
    """Removes a sid for a user. Returns the remaining active connection count."""
    sids = user_sids.get(user_id)
    if sids:
        sids.discard(sid)
        if not sids:
            user_sids.pop(user_id, None)
    return len(user_sids.get(user_id, set()))