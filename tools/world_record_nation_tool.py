from collections import defaultdict
from urllib.parse import parse_qs, urlparse

import requests
from bs4 import BeautifulSoup


RECORD_HISTORY_URL = (
    "https://maxithlon.com/varie/"
    "gare_record_storia.php"
)

MIN_SEASON = 20


EVENTS = (
    ("Men 100 Meters", 0, 1),
    ("Women 100 Meters", 1, 1),
    ("Men 200 Meters", 0, 4),
    ("Women 200 Meters", 1, 4),
    ("Men 400 Meters", 0, 6),
    ("Women 400 Meters", 1, 6),
    ("Men 110 Hurdles", 0, 23),
    ("Women 100 Hurdles", 1, 23),
    ("Men 400 Hurdles", 0, 25),
    ("Women 400 Hurdles", 1, 25),
    ("Men 800 Meters", 0, 8),
    ("Women 800 Meters", 1, 8),
    ("Men 1500 Meters", 0, 11),
    ("Women 1500 Meters", 1, 11),
    ("Men 3000 Steeplechase", 0, 19),
    ("Women 3000 Steeplechase", 1, 19),
    ("Men 5000 Meters", 0, 14),
    ("Women 5000 Meters", 1, 14),
    ("Men 10000 Meters", 0, 15),
    ("Women 10000 Meters", 1, 15),
    ("Men Marathon", 0, 53),
    ("Women Marathon", 1, 53),
    ("Men 10Km Race Walk", 0, 46),
    ("Women 10Km Race Walk", 1, 46),
    ("Men 20Km Race Walk", 0, 47),
    ("Women 20Km Race Walk", 1, 47),
    ("Men 50Km Race Walk", 0, 72),
    ("Women 50Km Race Walk", 1, 72),
    ("Men High Jump", 0, 26),
    ("Women High Jump", 1, 26),
    ("Men Pole Vault", 0, 27),
    ("Women Pole Vault", 1, 27),
    ("Men Long Jump", 0, 28),
    ("Women Long Jump", 1, 28),
    ("Men Triple Jump", 0, 29),
    ("Women Triple Jump", 1, 29),
    ("Men Shot Put", 0, 31),
    ("Women Shot Put", 1, 31),
    ("Men Discus Throw", 0, 32),
    ("Women Discus Throw", 1, 32),
    ("Men Hammer Throw", 0, 33),
    ("Women Hammer Throw", 1, 33),
    ("Men Javelin Throw", 0, 34),
    ("Women Javelin Throw", 1, 34),
    ("Men Relay 4x100", 0, 80),
    ("Women Relay 4x100", 1, 80),
    ("Men Relay 4x400", 0, 90),
    ("Women Relay 4x400", 1, 90),
    ("Men Pentathlon", 0, 99),
    ("Women Pentathlon", 1, 100),
    ("Men Decathlon", 0, 130),
    ("Women Heptathlon", 1, 120),
)


def extract_nation_id(
    href: str,
) -> int | None:
    parsed = urlparse(href)
    values = parse_qs(
        parsed.query
    ).get("n")

    if not values:
        return None

    try:
        return int(values[0])
    except (
        TypeError,
        ValueError,
    ):
        return None


def fetch_record_history(
    session: requests.Session,
    sex: int,
    event_id: int,
) -> str:
    response = session.get(
        RECORD_HISTORY_URL,
        params={
            "s": sex,
            "a": "4|0",
            "g": event_id,
        },
        timeout=15,
    )

    response.raise_for_status()

    return response.text


def extract_record_rows(
    html: str,
    minimum_season: int = MIN_SEASON,
) -> list[dict]:
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

    records = []

    for row in table.find_all(
        "tr",
    ):
        cells = row.find_all(
            "td",
            recursive=False,
        )

        if len(cells) < 4:
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

        nation_link = cells[
            2
        ].find(
            "a",
            href=lambda href: (
                href
                and "geo_nazione.php?n="
                in href
            ),
        )

        if nation_link is None:
            continue

        nation_id = extract_nation_id(
            nation_link.get(
                "href",
                "",
            )
        )

        flag = nation_link.find(
            "img"
        )

        nation_name = None

        if flag is not None:
            nation_name = flag.get(
                "title"
            )

        if not nation_name:
            nation_name = (
                nation_link.get_text(
                    " ",
                    strip=True,
                )
            )

        if not nation_name:
            nation_name = (
                f"Nation {nation_id}"
                if nation_id is not None
                else "Unknown"
            )

        records.append(
            {
                "season": season,
                "nation_id": nation_id,
                "nation": nation_name,
            }
        )

    return records


def add_records(
    counts: dict,
    records: list[dict],
):
    for record in records:
        nation_id = record[
            "nation_id"
        ]
        nation_name = record[
            "nation"
        ]

        key = (
            nation_id
            if nation_id is not None
            else nation_name
        )

        if key not in counts:
            counts[key] = {
                "nation_id": (
                    nation_id
                ),
                "nation": (
                    nation_name
                ),
                "records": 0,
            }

        counts[key][
            "records"
        ] += 1


def build_ranked_rows(
    counts: dict,
) -> list[dict]:
    rows = list(
        counts.values()
    )

    rows.sort(
        key=lambda row: (
            -row["records"],
            row["nation"].casefold(),
        )
    )

    ranked = []

    previous_count = None
    rank = 0

    for index, row in enumerate(
        rows,
        start=1,
    ):
        if (
            row["records"]
            != previous_count
        ):
            rank = index

        ranked.append(
            {
                "rank": rank,
                **row,
            }
        )

        previous_count = row[
            "records"
        ]

    return ranked


def calculate_wr_by_nation(
    session: requests.Session,
    progress_callback=None,
) -> dict:
    counts = {}
    errors = []

    total_events = len(EVENTS)
    completed = 0
    record_count = 0

    for (
        event_name,
        sex,
        event_id,
    ) in EVENTS:
        error = None
        event_records = []

        try:
            html = (
                fetch_record_history(
                    session,
                    sex,
                    event_id,
                )
            )

            event_records = (
                extract_record_rows(
                    html
                )
            )

            add_records(
                counts,
                event_records,
            )

            record_count += len(
                event_records
            )

        except Exception as exc:
            error = str(exc)

            errors.append(
                {
                    "event": event_name,
                    "sex": sex,
                    "event_id": (
                        event_id
                    ),
                    "error": error,
                }
            )

        completed += 1

        if (
            progress_callback
            is not None
        ):
            progress_callback(
                {
                    "current": completed,
                    "total": (
                        total_events
                    ),
                    "event": (
                        event_name
                    ),
                    "event_id": (
                        event_id
                    ),
                    "records_found": (
                        len(
                            event_records
                        )
                    ),
                    "record_count": (
                        record_count
                    ),
                    "error": error,
                }
            )

    return {
        "rows": build_ranked_rows(
            counts
        ),
        "event_count": total_events,
        "record_count": record_count,
        "errors": errors,
    }
