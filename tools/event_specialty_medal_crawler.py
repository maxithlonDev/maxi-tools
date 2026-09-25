from collections import defaultdict
import re

import requests

from tools.competition_income_tools import (
    extract_competition_events,
    extract_event_club_results,
    fetch_competition_details_html,
    fetch_event_result_html,
)


NATION_URL = (
    "https://maxithlon.com/geo/geo_nazione.php"
)


def get_target_competitions(
    history: dict,
    country_id: str,
    from_season: int,
    to_season: int,
) -> list[dict]:
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

    targets = []

    for season_key, competition in (
        competitions.items()
    ):
        try:
            season = int(season_key)
            competition_id = int(
                competition.get(
                    "competition_id"
                )
            )
        except (
            TypeError,
            ValueError,
            AttributeError,
        ):
            continue

        if not (
            minimum_season
            <= season
            <= maximum_season
        ):
            continue

        targets.append(
            {
                "season": season,
                "competition_id": (
                    competition_id
                ),
            }
        )

    return targets


def fetch_nation_html(
    session: requests.Session,
    country_id: str,
) -> str | None:
    try:
        response = session.get(
            NATION_URL,
            params={
                "n": country_id,
            },
        )
        response.raise_for_status()
        return response.text
    except requests.RequestException:
        return None


def normalize_event_name(
    name: str,
) -> str:
    value = name.casefold().strip()

    value = value.replace(
        "metres",
        "meters",
    )

    value = re.sub(
        r"\bmeters?\b",
        "",
        value,
    )

    value = re.sub(
        r"(\d+)\s*m\b",
        r"\1",
        value,
    )

    value = re.sub(
        r"\bmen\b",
        " men ",
        value,
    )

    value = re.sub(
        r"\bwomen\b",
        " women ",
        value,
    )

    value = re.sub(
        r"[^a-z0-9]+",
        " ",
        value,
    )

    return " ".join(
        value.split()
    )


def build_event_occurrences(
    competition_html: str,
) -> dict[str, list[tuple[int, str]]]:
    occurrences = defaultdict(list)

    try:
        events = extract_competition_events(
            competition_html
        )
    except Exception:
        return {}

    for event_id, event_name in events:
        normalized = normalize_event_name(
            event_name
        )

        occurrences[
            normalized
        ].append(
            (
                event_id,
                event_name,
            )
        )

    return dict(
        occurrences
    )


def get_target_aliases(
    event: dict,
) -> set[str]:
    event_name = event[
        "event_name"
    ]

    aliases = {
        normalize_event_name(
            event_name
        )
    }

    normalized = normalize_event_name(
        event_name
    )

    if normalized == "110 hurdles":
        aliases.update(
            {
                "110 hurdles",
                "110 hurdle",
            }
        )

    elif normalized == "100 hurdles":
        aliases.update(
            {
                "100 hurdles",
                "100 hurdle",
            }
        )

    elif normalized == "400 hurdles":
        aliases.update(
            {
                "400 hurdles",
                "400 hurdle",
            }
        )

    return aliases


def choose_event_id(
    occurrences: dict[
        str,
        list[tuple[int, str]],
    ],
    event: dict,
) -> int | None:
    aliases = get_target_aliases(
        event
    )

    candidates = []

    for alias in aliases:
        candidates.extend(
            occurrences.get(
                alias,
                [],
            )
        )

    if not candidates:
        target = normalize_event_name(
            event["event_name"]
        )

        for (
            normalized_name,
            values,
        ) in occurrences.items():
            if (
                normalized_name == target
                or target
                in normalized_name
                or normalized_name
                in target
            ):
                candidates.extend(
                    values
                )

    if not candidates:
        return None

    unique_candidates = []
    seen_ids = set()

    for event_id, event_name in candidates:
        if event_id in seen_ids:
            continue

        seen_ids.add(
            event_id
        )

        unique_candidates.append(
            (
                event_id,
                event_name,
            )
        )

    if not unique_candidates:
        return None

    if len(unique_candidates) == 1:
        return unique_candidates[
            0
        ][0]

    if event["sex"] == "Women":
        return unique_candidates[
            -1
        ][0]

    return unique_candidates[
        0
    ][0]


def build_club_metadata(
    history: dict,
    country_id: str,
) -> tuple[dict, dict]:
    country = history[
        "countries"
    ].get(
        str(country_id),
        {},
    )

    by_id = {}
    by_name = {}

    for competition in (
        country.get(
            "competitions",
            {},
        ).values()
    ):
        for club in competition.get(
            "clubs",
            [],
        ):
            club_id = club.get(
                "club_id"
            )
            club_name = club.get(
                "name",
                "",
            )

            metadata = {
                "nation_id": club.get(
                    "nation_id"
                ),
                "nationality": club.get(
                    "nationality"
                ),
                "nation_code": club.get(
                    "nation_code"
                ),
            }

            if club_id is not None:
                by_id[
                    club_id
                ] = metadata

            if club_name:
                by_name[
                    club_name
                ] = metadata

    return (
        by_id,
        by_name,
    )


def get_club_metadata(
    club_id,
    club_name: str,
    by_id: dict,
    by_name: dict,
) -> dict:
    if (
        club_id is not None
        and club_id in by_id
    ):
        return by_id[
            club_id
        ]

    return by_name.get(
        club_name,
        {},
    )


def add_medal(
    medals: dict,
    *,
    club_id,
    club_name: str,
    place: int,
    metadata: dict,
):
    key = (
        (
            "id",
            club_id,
        )
        if club_id is not None
        else (
            "name",
            club_name,
        )
    )

    if key not in medals:
        medals[key] = {
            "club_id": club_id,
            "name": club_name,
            "nation_id": (
                metadata.get(
                    "nation_id"
                )
            ),
            "nationality": (
                metadata.get(
                    "nationality"
                )
            ),
            "nation_code": (
                metadata.get(
                    "nation_code"
                )
            ),
            "gold": 0,
            "silver": 0,
            "bronze": 0,
        }

    if place == 1:
        medals[key][
            "gold"
        ] += 1

    elif place == 2:
        medals[key][
            "silver"
        ] += 1

    elif place == 3:
        medals[key][
            "bronze"
        ] += 1


def merge_unlinked_clubs(
    medals: dict,
):
    linked_by_name = defaultdict(
        list
    )

    for key, club in medals.items():
        if club[
            "club_id"
        ] is None:
            continue

        linked_by_name[
            club["name"]
        ].append(
            key
        )

    remove_keys = []

    for key, club in list(
        medals.items()
    ):
        if club[
            "club_id"
        ] is not None:
            continue

        matches = (
            linked_by_name.get(
                club["name"],
                [],
            )
        )

        if len(matches) != 1:
            continue

        target = medals[
            matches[0]
        ]

        target[
            "gold"
        ] += club["gold"]

        target[
            "silver"
        ] += club["silver"]

        target[
            "bronze"
        ] += club["bronze"]

        remove_keys.append(
            key
        )

    for key in remove_keys:
        del medals[
            key
        ]


def sort_medals(
    medals: dict,
) -> list[dict]:
    clubs = list(
        medals.values()
    )

    clubs.sort(
        key=lambda club: (
            (
                club["club_id"] is None
                and club["name"]
                == "No Club"
            ),
            -club["gold"],
            -club["silver"],
            -club["bronze"],
            club["name"].casefold(),
        )
    )

    return clubs


def crawl_event_medals(
    *,
    session: requests.Session,
    history: dict,
    country_id: str,
    from_season: int,
    to_season: int,
    selected_events: list[dict],
    progress_callback=None,
) -> dict:
    targets = get_target_competitions(
        history,
        country_id,
        from_season,
        to_season,
    )

    inc_total = len(
        targets
    )

    events_per_inc = len(
        selected_events
    )

    event_total = (
        inc_total
        * events_per_inc
    )

    page_total = (
        1
        + inc_total
        + event_total
    )

    page_current = 0
    event_current = 0
    skipped = []

    def report(
        *,
        phase: str,
        inc_current: int,
    ):
        if progress_callback is None:
            return

        try:
            progress_callback(
                {
                    "phase": phase,
                    "page_current": (
                        page_current
                    ),
                    "page_total": (
                        page_total
                    ),
                    "inc_current": (
                        inc_current
                    ),
                    "inc_total": (
                        inc_total
                    ),
                    "event_current": (
                        event_current
                    ),
                    "event_total": (
                        event_total
                    ),
                }
            )
        except Exception:
            pass

    fetch_nation_html(
        session,
        country_id,
    )

    page_current += 1

    report(
        phase="nation",
        inc_current=0,
    )

    (
        metadata_by_id,
        metadata_by_name,
    ) = build_club_metadata(
        history,
        country_id,
    )

    medals = {}

    for inc_index, target in enumerate(
        targets,
        start=1,
    ):
        competition_html = None

        try:
            competition_html = (
                fetch_competition_details_html(
                    session,
                    target[
                        "competition_id"
                    ],
                )
            )
        except Exception as exc:
            skipped.append(
                {
                    "season": target[
                        "season"
                    ],
                    "competition_id": target[
                        "competition_id"
                    ],
                    "event": None,
                    "reason": str(exc),
                }
            )

        page_current += 1

        report(
            phase="inc",
            inc_current=inc_index,
        )

        if competition_html is None:
            for event in selected_events:
                event_current += 1
                page_current += 1

                skipped.append(
                    {
                        "season": target[
                            "season"
                        ],
                        "competition_id": target[
                            "competition_id"
                        ],
                        "event": event[
                            "event_name"
                        ],
                        "reason": (
                            "Competition page "
                            "could not be loaded."
                        ),
                    }
                )

                report(
                    phase="event",
                    inc_current=(
                        inc_index
                    ),
                )

            continue

        occurrences = (
            build_event_occurrences(
                competition_html
            )
        )

        for event in selected_events:
            event_current += 1

            event_id = (
                choose_event_id(
                    occurrences,
                    event,
                )
            )

            if event_id is None:
                page_current += 1

                skipped.append(
                    {
                        "season": target[
                            "season"
                        ],
                        "competition_id": target[
                            "competition_id"
                        ],
                        "event": event[
                            "event_name"
                        ],
                        "reason": (
                            "Matching event "
                            "was not found."
                        ),
                    }
                )

                report(
                    phase="event",
                    inc_current=(
                        inc_index
                    ),
                )

                continue

            event_html = None

            try:
                event_html = (
                    fetch_event_result_html(
                        session,
                        event_id,
                    )
                )
            except Exception as exc:
                skipped.append(
                    {
                        "season": target[
                            "season"
                        ],
                        "competition_id": target[
                            "competition_id"
                        ],
                        "event": event[
                            "event_name"
                        ],
                        "reason": str(
                            exc
                        ),
                    }
                )

            page_current += 1

            if event_html is not None:
                try:
                    event_results = (
                        extract_event_club_results(
                            event_html,
                            paid_places=3,
                            first_place_income=1,
                        )
                    )
                except Exception as exc:
                    skipped.append(
                        {
                            "season": target[
                                "season"
                            ],
                            "competition_id": target[
                                "competition_id"
                            ],
                            "event": event[
                                "event_name"
                            ],
                            "reason": str(
                                exc
                            ),
                        }
                    )

                    event_results = []

                for result in event_results:
                    place = result.get(
                        "place"
                    )

                    if place not in (
                        1,
                        2,
                        3,
                    ):
                        continue

                    club_id = (
                        result.get(
                            "club_id"
                        )
                    )

                    club_name = (
                        result.get(
                            "name",
                            "No Club",
                        )
                    )

                    metadata = (
                        get_club_metadata(
                            club_id,
                            club_name,
                            metadata_by_id,
                            metadata_by_name,
                        )
                    )

                    add_medal(
                        medals,
                        club_id=club_id,
                        club_name=club_name,
                        place=place,
                        metadata=metadata,
                    )

            report(
                phase="event",
                inc_current=inc_index,
            )

    merge_unlinked_clubs(
        medals
    )

    return {
        "clubs": sort_medals(
            medals
        ),
        "inc_count": inc_total,
        "event_count": event_total,
        "page_count": page_total,
        "skipped": skipped,
    }
