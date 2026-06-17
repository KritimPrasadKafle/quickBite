from shared.enums import RestaurantStatus


# Which target states are reachable FROM each current state.
RESTAURANT_TRANSITIONS: dict[RestaurantStatus, set[RestaurantStatus]] = {
    RestaurantStatus.pending: {
        RestaurantStatus.active,      # approve the application
        RestaurantStatus.suspended,   # reject a bad application outright
    },
    RestaurantStatus.active: {
        RestaurantStatus.suspended,   # take down a live restaurant
    },
    RestaurantStatus.suspended: {
        RestaurantStatus.active,      # reinstate
    },
}


def can_transition(current: RestaurantStatus, target: RestaurantStatus) -> bool:
    """True if moving current → target is a legal transition."""
    if current == target:
        return False  # no-op transitions are not meaningful
    return target in RESTAURANT_TRANSITIONS.get(current, set())


def assert_can_transition(current: RestaurantStatus, target: RestaurantStatus) -> None:
    """Raise ValueError if the transition is illegal. Service layer translates to HTTP."""
    if not can_transition(current, target):
        allowed = RESTAURANT_TRANSITIONS.get(current, set())
        allowed_str = ", ".join(s.value for s in allowed) or "none"
        raise ValueError(
            f"Cannot change status from {current.value} to {target.value}. "
            f"Allowed from {current.value}: {allowed_str}."
        )