SECONDS_PER_PAGE = 0.3


def count_inc_competitions(
    history: dict,
    country_id: str,
    from_season: int,
    to_season: int,
) -> int:
    country = history["countries"].get(
        str(country_id),
        {},
    )

    competitions = country.get(
        "competitions",
        {},
    )

    minimum_season = min(
        from_season,
        to_season,
    )
    maximum_season = max(
        from_season,
        to_season,
    )

    return sum(
        1
        for season_key in competitions
        if (
            str(season_key).isdigit()
            and minimum_season
            <= int(season_key)
            <= maximum_season
        )
    )


def build_load_estimate(
    *,
    inc_count: int,
    events_per_inc: int,
) -> dict:
    event_pages = (
        inc_count
        * events_per_inc
    )

    total_pages = (
        1
        + inc_count
        + event_pages
    )

    eta_seconds = (
        total_pages
        * SECONDS_PER_PAGE
    )

    return {
        "inc_count": inc_count,
        "event_pages": event_pages,
        "total_pages": total_pages,
        "eta_seconds": eta_seconds,
    }


def format_eta(
    seconds: float,
) -> str:
    rounded_seconds = int(
        round(seconds)
    )

    if rounded_seconds < 60:
        return f"{rounded_seconds}s"

    minutes, remaining_seconds = divmod(
        rounded_seconds,
        60,
    )

    if remaining_seconds == 0:
        return f"{minutes}m"

    return (
        f"{minutes}m "
        f"{remaining_seconds}s"
    )


def format_load_estimate(
    estimate: dict,
) -> str:
    return (
        f"{estimate['inc_count']} INC competitions"
        f" · "
        f"{estimate['event_pages']} event results"
        f" · "
        f"{estimate['total_pages']} pages"
        f" · "
        f"ETA ~{format_eta(estimate['eta_seconds'])}"
    )
