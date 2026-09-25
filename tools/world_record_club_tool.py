import csv
from pathlib import Path
from urllib.parse import parse_qs, urlparse

from bs4 import BeautifulSoup

from tools.competition_income_tools import (
    NO_CLUB_NAME,
    extract_event_club_results,
    fetch_event_result_html,
)
from tools.world_record_nation_tool import (
    EVENTS,
    MIN_SEASON,
    fetch_record_history,
)


ROOT_DIR = Path(__file__).resolve().parent.parent

CLUB_CSV_PATH = (
    ROOT_DIR
    / "data"
    / "world_records_by_club_season_20_plus.csv"
)

UNKNOWN_CLUB = "Unknown"


def extract_event_result_id(
    href: str,
) -> int | None:
    parsed = urlparse(href)

    values = parse_qs(
        parsed.query
    ).get("e")

    if not values:
        return None

    try:
        return int(
            values[0]
        )
    except (
        TypeError,
        ValueError,
    ):
        return None


def extract_record_event_ids(
    html: str,
    minimum_season: int = MIN_SEASON,
) -> list[int | None]:
    soup = BeautifulSoup(
        html,
        "html.parser",
    )

    table = soup.find(
        "table",
        class_="results",
    )

    if table is None:
        return []

    event_ids = []

    for row in table.find_all(
        "tr",
    ):
        cells = row.find_all(
            "td",
            recursive=False,
        )

        if len(cells) < 5:
            continue

        season_text = cells[
            0
        ].get_text(
            " ",
            strip=True,
        )

        try:
            season = int(
                season_text
            )
        except (
            TypeError,
            ValueError,
        ):
            continue

        if season < minimum_season:
            continue

        result_link = cells[
            4
        ].find(
            "a",
            href=lambda href: (
                href
                and "risultati_gara.php?e="
                in href
            ),
        )

        if result_link is None:
            event_ids.append(
                None
            )
            continue

        event_ids.append(
            extract_event_result_id(
                result_link.get(
                    "href",
                    "",
                )
            )
        )

    return event_ids


def normalize_club_name(
    club_name: str | None,
) -> str:
    if not club_name:
        return UNKNOWN_CLUB

    club_name = club_name.strip()

    if (
        not club_name
        or club_name == NO_CLUB_NAME
    ):
        return UNKNOWN_CLUB

    return club_name


def extract_winning_club(
    html: str,
) -> tuple[int | None, str]:
    results = (
        extract_event_club_results(
            html,
            paid_places=1,
            first_place_income=1,
        )
    )

    if not results:
        return (
            None,
            UNKNOWN_CLUB,
        )

    winner = results[0]

    return (
        winner.get(
            "club_id"
        ),
        normalize_club_name(
            winner.get(
                "name"
            )
        ),
    )


def get_club_key(
    club_id: int | None,
    club_name: str,
):
    if club_name == UNKNOWN_CLUB:
        return (
            "unknown",
            UNKNOWN_CLUB,
        )

    if club_id is not None:
        return (
            "id",
            club_id,
        )

    return (
        "name",
        club_name,
    )


def add_club_record(
    counts: dict,
    club_id: int | None,
    club_name: str,
):
    key = get_club_key(
        club_id,
        club_name,
    )

    if key not in counts:
        counts[key] = {
            "club_id": club_id,
            "club": club_name,
            "records": 0,
        }

    counts[key][
        "records"
    ] += 1


def build_ranked_rows(
    counts: dict,
) -> list[dict]:
    known = [
        row
        for row in counts.values()
        if row["club"]
        != UNKNOWN_CLUB
    ]

    unknown = [
        row
        for row in counts.values()
        if row["club"]
        == UNKNOWN_CLUB
    ]

    known.sort(
        key=lambda row: (
            -row["records"],
            row["club"].casefold(),
        )
    )

    rows = []
    previous_count = None
    rank = 0

    for index, row in enumerate(
        known,
        start=1,
    ):
        if (
            row["records"]
            != previous_count
        ):
            rank = index

        rows.append(
            {
                "Rank": rank,
                "Club": row[
                    "club"
                ],
                "WRs": row[
                    "records"
                ],
            }
        )

        previous_count = row[
            "records"
        ]

    for row in unknown:
        rows.append(
            {
                "Rank": "",
                "Club": UNKNOWN_CLUB,
                "WRs": row[
                    "records"
                ],
            }
        )

    return rows


def save_club_csv(
    rows: list[dict],
):
    CLUB_CSV_PATH.parent.mkdir(
        parents=True,
        exist_ok=True,
    )

    with CLUB_CSV_PATH.open(
        "w",
        encoding="utf-8",
        newline="",
    ) as file:
        writer = csv.DictWriter(
            file,
            fieldnames=(
                "Rank",
                "Club",
                "WRs",
            ),
        )

        writer.writeheader()
        writer.writerows(
            rows
        )


def crawl_wr_clubs(
    session,
    progress_callback=None,
) -> dict:
    counts = {}
    errors = []

    total_history_pages = len(
        EVENTS
    )

    completed_pages = 0
    total_record_pages = 0
    processed_records = 0

    event_result_cache = {}

    event_record_ids = []

    for (
        event_index,
        (
            event_name,
            sex,
            event_id,
        ),
    ) in enumerate(
        EVENTS,
        start=1,
    ):
        try:
            history_html = (
                fetch_record_history(
                    session,
                    sex,
                    event_id,
                )
            )

            record_ids = (
                extract_record_event_ids(
                    history_html
                )
            )

        except Exception as exc:
            record_ids = []

            errors.append(
                {
                    "event": event_name,
                    "error": str(
                        exc
                    ),
                }
            )

        event_record_ids.append(
            (
                event_name,
                record_ids,
            )
        )

        total_record_pages += len(
            record_ids
        )

        completed_pages += 1

        if (
            progress_callback
            is not None
        ):
            progress_callback(
                {
                    "phase": "history",
                    "event_current": (
                        event_index
                    ),
                    "event_total": (
                        total_history_pages
                    ),
                    "event": (
                        event_name
                    ),
                    "record_current": 0,
                    "record_total": (
                        total_record_pages
                    ),
                    "page_current": (
                        completed_pages
                    ),
                    "page_total": (
                        total_history_pages
                        + total_record_pages
                    ),
                }
            )

    total_pages = (
        total_history_pages
        + total_record_pages
    )

    for (
        event_name,
        record_ids,
    ) in event_record_ids:
        for event_result_id in (
            record_ids
        ):
            processed_records += 1

            if (
                event_result_id
                is None
            ):
                add_club_record(
                    counts,
                    None,
                    UNKNOWN_CLUB,
                )

                completed_pages += 1

            elif (
                event_result_id
                in event_result_cache
            ):
                (
                    club_id,
                    club_name,
                ) = event_result_cache[
                    event_result_id
                ]

                add_club_record(
                    counts,
                    club_id,
                    club_name,
                )

            else:
                try:
                    event_html = (
                        fetch_event_result_html(
                            session,
                            event_result_id,
                        )
                    )

                    (
                        club_id,
                        club_name,
                    ) = (
                        extract_winning_club(
                            event_html
                        )
                    )

                except Exception as exc:
                    club_id = None
                    club_name = (
                        UNKNOWN_CLUB
                    )

                    errors.append(
                        {
                            "event": (
                                event_name
                            ),
                            "event_id": (
                                event_result_id
                            ),
                            "error": str(
                                exc
                            ),
                        }
                    )

                event_result_cache[
                    event_result_id
                ] = (
                    club_id,
                    club_name,
                )

                add_club_record(
                    counts,
                    club_id,
                    club_name,
                )

                completed_pages += 1

            if (
                progress_callback
                is not None
            ):
                progress_callback(
                    {
                        "phase": (
                            "records"
                        ),
                        "event_current": (
                            total_history_pages
                        ),
                        "event_total": (
                            total_history_pages
                        ),
                        "event": (
                            event_name
                        ),
                        "record_current": (
                            processed_records
                        ),
                        "record_total": (
                            total_record_pages
                        ),
                        "page_current": (
                            completed_pages
                        ),
                        "page_total": (
                            total_pages
                        ),
                    }
                )

    rows = build_ranked_rows(
        counts
    )

    save_club_csv(
        rows
    )

    return {
        "rows": rows,
        "record_count": (
            total_record_pages
        ),
        "page_count": (
            completed_pages
        ),
        "errors": errors,
        "path": str(
            CLUB_CSV_PATH
        ),
    }
