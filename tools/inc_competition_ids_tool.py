import json
import threading
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path
from urllib.parse import parse_qs, urlparse

import requests
from bs4 import BeautifulSoup


ROOT_DIR = Path(__file__).resolve().parent.parent

INC_INDEX_PATHS = (
    ROOT_DIR / "Data" / "inc_competitions.json",
    ROOT_DIR / "data" / "inc_competitions.json",
)

INC_STATS_URL = (
    "https://maxithlon.com/manifestazioni/man_stat.php"
)

INC_STATS_WORKERS = 8

_thread_local = threading.local()


def find_inc_index_path() -> Path:
    for path in INC_INDEX_PATHS:
        if path.is_file():
            return path

    raise FileNotFoundError(
        "Could not find inc_competitions.json in Data/ or data/"
    )


def load_inc_index() -> dict:
    path = find_inc_index_path()

    with path.open(
        "r",
        encoding="utf-8",
    ) as file:
        data = json.load(file)

    countries = data.get("countries")

    if not isinstance(countries, dict):
        raise ValueError(
            "INC index is missing a valid countries object"
        )

    return data


def get_inc_country_ids(
    start_country_id: int = 1,
) -> list[int]:
    index_data = load_inc_index()
    countries = index_data["countries"]

    country_ids = []

    for country_id_value, country_data in (
        countries.items()
    ):
        try:
            country_id = int(country_id_value)
        except (TypeError, ValueError):
            continue

        if country_id < start_country_id:
            continue

        if not isinstance(country_data, dict):
            continue

        competitions = country_data.get(
            "competitions"
        )

        if (
            not isinstance(competitions, dict)
            or not competitions
        ):
            continue

        country_ids.append(country_id)

    country_ids.sort()

    return country_ids


def get_target_competitions(
    index_data: dict,
    country_id: int,
) -> tuple[str, list[dict]]:
    countries = index_data["countries"]
    country_key = str(country_id)
    country_data = countries.get(country_key)

    if not isinstance(country_data, dict):
        raise ValueError(
            f"Country {country_id} is missing from the INC index"
        )

    country_name = country_data.get("name")

    if (
        not isinstance(country_name, str)
        or not country_name
    ):
        raise ValueError(
            f"Country {country_id} has no valid display name"
        )

    competitions = country_data.get(
        "competitions"
    )

    if not isinstance(competitions, dict):
        raise ValueError(
            f"{country_name} has no valid competitions object"
        )

    targets = []

    # Preserve the exact order from inc_competitions.json.
    for (
        season_value,
        competition_value,
    ) in competitions.items():
        try:
            season = int(season_value)
            competition_id = int(
                competition_value
            )
        except (TypeError, ValueError):
            continue

        if season <= 0 or competition_id <= 0:
            continue

        targets.append(
            {
                "country_id": country_id,
                "country_name": country_name,
                "season": season,
                "competition_id": competition_id,
            }
        )

    if not targets:
        raise ValueError(
            f"{country_name} has no valid INC competitions"
        )

    return country_name, targets


def make_filename(
    country_id: int,
) -> str:
    return (
        f"inc_{country_id}_all_seasons.json"
    )


def build_country_json(
    country_id: int,
    country_name: str,
    results: list[dict],
    last_updated_season: int,
) -> bytes:
    competitions = {}

    for result in results:
        competitions[str(result["season"])] = {
            "competition_id": (
                result["competition_id"]
            ),
            "clubs": result["clubs"],
        }

    data = {
        "last_updated_season": (
            last_updated_season
        ),
        "countries": {
            str(country_id): {
                "name": country_name,
                "competitions": competitions,
            }
        },
    }

    return (
        json.dumps(
            data,
            ensure_ascii=False,
            indent=2,
        )
        + "\n"
    ).encode("utf-8")


def get_worker_session(
    source_session: requests.Session,
) -> requests.Session:
    worker_session = getattr(
        _thread_local,
        "session",
        None,
    )

    if worker_session is None:
        worker_session = requests.Session()

        worker_session.headers.update(
            source_session.headers
        )

        worker_session.cookies.update(
            source_session.cookies
        )

        _thread_local.session = (
            worker_session
        )

    return worker_session


def extract_club_id(
    href: str | None,
) -> int | None:
    if not href:
        return None

    parsed = urlparse(href)
    values = parse_qs(
        parsed.query
    ).get("u")

    if not values:
        return None

    try:
        club_id = int(values[0])
    except (TypeError, ValueError):
        return None

    if club_id <= 0:
        return None

    return club_id


def find_medals_by_team_table(
    soup: BeautifulSoup,
):
    label = soup.find(
        string=lambda text: (
            isinstance(text, str)
            and "Medals Table by team:"
            in text
        )
    )

    if label is None:
        return None

    table = label.find_next(
        "table",
        class_="man_details",
    )

    return table


def parse_medals_by_team(
    html: str,
) -> list[dict]:
    soup = BeautifulSoup(
        html,
        "html.parser",
    )

    table = find_medals_by_team_table(
        soup
    )

    if table is None:
        raise ValueError(
            "Medals Table by team not found"
        )

    clubs = []

    rows = table.find_all(
        "tr",
        recursive=False,
    )

    for row in rows:
        cells = row.find_all(
            "td",
            recursive=False,
        )

        if len(cells) < 4:
            continue

        total_cells = row.find_all(
            "td",
            class_="total_color",
            recursive=False,
        )

        if len(total_cells) != 3:
            continue

        if len(cells) < 3:
            continue

        club_cell = cells[2]

        club_link = club_cell.find(
            "a",
            href=lambda href: (
                href
                and "dettagli_societa.php?u="
                in href
            ),
        )

        if club_link is not None:
            club_id = extract_club_id(
                club_link.get("href")
            )

            club_name = (
                club_link.get_text(
                    " ",
                    strip=True,
                )
            )
        else:
            club_id = None

            club_name = (
                club_cell.get_text(
                    " ",
                    strip=True,
                )
            )

        if not club_name:
            club_name = "No Club"

        try:
            gold = int(
                total_cells[0].get_text(
                    " ",
                    strip=True,
                )
            )
            silver = int(
                total_cells[1].get_text(
                    " ",
                    strip=True,
                )
            )
            bronze = int(
                total_cells[2].get_text(
                    " ",
                    strip=True,
                )
            )
        except (TypeError, ValueError):
            continue

        clubs.append(
            {
                "club_id": club_id,
                "name": club_name,
                "gold": gold,
                "silver": silver,
                "bronze": bronze,
            }
        )

    return clubs


def fetch_competition_medals(
    source_session: requests.Session,
    target: dict,
) -> dict:
    start = time.perf_counter()

    try:
        session = get_worker_session(
            source_session
        )

        response = session.get(
            INC_STATS_URL,
            params={
                "m": target["competition_id"],
            },
            timeout=30,
        )

        response.raise_for_status()

        clubs = parse_medals_by_team(
            response.text
        )

        return {
            "season": target["season"],
            "competition_id": (
                target["competition_id"]
            ),
            "clubs": clubs,
            "elapsed_seconds": (
                time.perf_counter()
                - start
            ),
            "error": None,
        }

    except Exception as exc:
        return {
            "season": target["season"],
            "competition_id": (
                target["competition_id"]
            ),
            "clubs": None,
            "elapsed_seconds": (
                time.perf_counter()
                - start
            ),
            "error": str(exc),
        }


def get_inc_competitions_json(
    session: requests.Session,
    country_id: int,
    progress_callback=None,
) -> dict:
    wall_start = time.perf_counter()

    index_data = load_inc_index()

    country_name, targets = (
        get_target_competitions(
            index_data,
            country_id,
        )
    )

    total_seasons = len(targets)

    results_by_season = {}
    errors = []
    timings_by_season = {}

    completed = 0

    with ThreadPoolExecutor(
        max_workers=INC_STATS_WORKERS
    ) as executor:
        future_to_target = {
            executor.submit(
                fetch_competition_medals,
                session,
                target,
            ): target
            for target in targets
        }

        for future in as_completed(
            future_to_target
        ):
            target = future_to_target[
                future
            ]

            try:
                result = future.result()
            except Exception as exc:
                result = {
                    "season": target["season"],
                    "competition_id": (
                        target[
                            "competition_id"
                        ]
                    ),
                    "clubs": None,
                    "elapsed_seconds": 0.0,
                    "error": str(exc),
                }

            completed += 1

            timings_by_season[
                target["season"]
            ] = result[
                "elapsed_seconds"
            ]

            if result["error"] is None:
                results_by_season[
                    target["season"]
                ] = result
            else:
                errors.append(
                    {
                        "season": (
                            target["season"]
                        ),
                        "competition_id": (
                            target[
                                "competition_id"
                            ]
                        ),
                        "error": (
                            result["error"]
                        ),
                    }
                )

            if (
                progress_callback
                is not None
            ):
                elapsed_seconds = (
                    time.perf_counter()
                    - wall_start
                )

                pages_per_second = (
                    completed
                    / elapsed_seconds
                    if elapsed_seconds > 0
                    else 0.0
                )

                progress_callback(
                    {
                        "phase": "stats",
                        "current": completed,
                        "total": total_seasons,
                        "country_id": (
                            country_id
                        ),
                        "country_name": (
                            country_name
                        ),
                        "season": (
                            target["season"]
                        ),
                        "competition_id": (
                            target[
                                "competition_id"
                            ]
                        ),
                        "successful": len(
                            results_by_season
                        ),
                        "failed": len(
                            errors
                        ),
                        "elapsed_seconds": (
                            elapsed_seconds
                        ),
                        "pages_per_second": (
                            pages_per_second
                        ),
                    }
                )

    successful_results = [
        results_by_season[
            target["season"]
        ]
        for target in targets
        if (
            target["season"]
            in results_by_season
        )
    ]

    timings = [
        {
            "country_id": country_id,
            "country_name": country_name,
            "season": target["season"],
            "competition_id": (
                target["competition_id"]
            ),
            "fetch_seconds": (
                timings_by_season.get(
                    target["season"],
                    0.0,
                )
            ),
        }
        for target in targets
    ]

    outputs = []

    if successful_results:
        index_last_updated = (
            index_data.get(
                "last_updated_season"
            )
        )

        try:
            last_updated_season = int(
                index_last_updated
            )
        except (
            TypeError,
            ValueError,
        ):
            last_updated_season = (
                targets[0]["season"]
            )

        outputs.append(
            {
                "country_id": (
                    country_id
                ),
                "country_name": (
                    country_name
                ),
                "file_name": make_filename(
                    country_id
                ),
                "json_data": (
                    build_country_json(
                        country_id,
                        country_name,
                        successful_results,
                        last_updated_season,
                    )
                ),
            }
        )

    total_elapsed_seconds = (
        time.perf_counter()
        - wall_start
    )

    latest_season = (
        targets[0]["season"]
        if targets
        else None
    )

    return {
        "outputs": outputs,
        "timings": timings,
        "country_id": country_id,
        "country_name": country_name,
        "country_count": 1,
        "competition_count": len(
            targets
        ),
        "successful_competition_count": (
            len(successful_results)
        ),
        "failed_competition_count": (
            len(errors)
        ),
        "requested_competition_count": (
            len(targets)
        ),
        "latest_season": latest_season,
        "total_elapsed_seconds": (
            total_elapsed_seconds
        ),
        "page_count": len(targets),
        "pages_per_second": (
            len(targets)
            / total_elapsed_seconds
            if total_elapsed_seconds > 0
            else 0.0
        ),
        "errors": errors,
    }
