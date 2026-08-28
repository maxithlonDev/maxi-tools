import json
import re
import time
from pathlib import Path

import requests

from tools.competition_income_tools import (
    collect_competition_club_stats,
    fetch_competition_details_html,
    validate_official_individual_competition,
)


ROOT_DIR = Path(__file__).resolve().parent.parent

INC_INDEX_PATHS = (
    ROOT_DIR / "Data" / "inc_competitions.json",
    ROOT_DIR / "data" / "inc_competitions.json",
)

TARGET_COUNTRY_IDS = (
    1,   # Italia
    18,  # United States
    57,  # Al-Jazā'ir
)

TARGET_SEASON = 107


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


def get_target_competitions(
    index_data: dict,
) -> list[dict]:
    countries = index_data["countries"]
    targets = []

    for country_id in TARGET_COUNTRY_IDS:
        country_key = str(country_id)
        country_data = countries.get(country_key)

        if not isinstance(country_data, dict):
            raise ValueError(
                f"Country {country_id} is missing from the INC index"
            )

        country_name = country_data.get("name")

        if not isinstance(country_name, str) or not country_name:
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

        competition_id = competitions.get(
            str(TARGET_SEASON)
        )

        if competition_id is None:
            raise ValueError(
                f"{country_name} has no INC competition "
                f"for season {TARGET_SEASON}"
            )

        try:
            competition_id = int(competition_id)
        except (TypeError, ValueError) as exc:
            raise ValueError(
                f"{country_name} has an invalid INC competition ID "
                f"for season {TARGET_SEASON}"
            ) from exc

        targets.append(
            {
                "country_id": country_id,
                "country_name": country_name,
                "competition_id": competition_id,
            }
        )

    return targets


def make_filename(
    country_name: str,
) -> str:
    filename_name = re.sub(
        r"[^a-zA-Z0-9]+",
        "_",
        country_name,
    ).strip("_").lower()

    return (
        f"inc_{filename_name}_"
        f"{TARGET_SEASON}.json"
    )


def build_country_json(
    country_id: int,
    country_name: str,
    competition_id: int,
    clubs: list[dict],
) -> bytes:
    data = {
        "last_updated_season": TARGET_SEASON,
        "countries": {
            str(country_id): {
                "name": country_name,
                "competitions": {
                    str(TARGET_SEASON): {
                        "competition_id": (
                            competition_id
                        ),
                        "clubs": clubs,
                    }
                },
            }
        },
    }

    return json.dumps(
        data,
        ensure_ascii=False,
        indent=2,
    ).encode("utf-8")


def get_inc_competitions_json(
    session: requests.Session,
    progress_callback=None,
) -> dict:
    index_data = load_inc_index()
    targets = get_target_competitions(
        index_data
    )

    outputs = []
    timings = []
    total = len(targets)

    for current, target in enumerate(
        targets,
        start=1,
    ):
        country_id = target["country_id"]
        country_name = target["country_name"]
        competition_id = target[
            "competition_id"
        ]

        if progress_callback is not None:
            progress_callback(
                current,
                total,
                country_id,
                country_name,
            )

        start_time = time.perf_counter()

        competition_html = (
            fetch_competition_details_html(
                session,
                competition_id,
            )
        )

        validate_official_individual_competition(
            competition_html
        )

        clubs = collect_competition_club_stats(
            session,
            competition_html,
        )

        elapsed_seconds = (
            time.perf_counter()
            - start_time
        )

        json_data = build_country_json(
            country_id,
            country_name,
            competition_id,
            clubs,
        )

        outputs.append(
            {
                "country_id": country_id,
                "country_name": country_name,
                "competition_id": competition_id,
                "file_name": make_filename(
                    country_name
                ),
                "json_data": json_data,
            }
        )

        timings.append(
            {
                "country_id": country_id,
                "country_name": country_name,
                "elapsed_seconds": (
                    elapsed_seconds
                ),
            }
        )

    return {
        "outputs": outputs,
        "timings": timings,
        "country_count": total,
        "competition_count": total,
        "latest_season": TARGET_SEASON,
    }
