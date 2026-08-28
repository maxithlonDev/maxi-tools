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
        if path.exists():
            return path

    raise FileNotFoundError(
        "Could not find Data/inc_competitions.json "
        "or data/inc_competitions.json"
    )


def load_inc_index() -> dict:
    path = find_inc_index_path()

    with path.open("r", encoding="utf-8") as file:
        data = json.load(file)

    if "countries" not in data:
        raise ValueError(
            "INC competition index has no countries"
        )

    return data


def get_target_competitions(
    index_data: dict,
) -> list[tuple[str, str, int]]:
    competitions = []

    for target_country_id in TARGET_COUNTRY_IDS:
        country_id = str(target_country_id)

        country_data = index_data["countries"].get(
            country_id
        )

        if country_data is None:
            raise ValueError(
                f"Country ID {target_country_id} not found"
            )

        competition_id = country_data[
            "competitions"
        ].get(
            str(TARGET_SEASON)
        )

        if competition_id is None:
            raise ValueError(
                f"No season {TARGET_SEASON} INC found "
                f"for country ID {target_country_id}"
            )

        competitions.append(
            (
                country_id,
                country_data["name"],
                int(competition_id),
            )
        )

    return competitions


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
    country_id: str,
    country_name: str,
    competition_id: int,
    club_stats: list[dict],
) -> bytes:
    data = {
        "last_updated_season": TARGET_SEASON,
        "countries": {
            country_id: {
                "name": country_name,
                "competitions": {
                    str(TARGET_SEASON): {
                        "competition_id": competition_id,
                        "clubs": club_stats,
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
) -> tuple[
    list[dict],
    list[dict],
    int,
    int,
    int,
]:
    index_data = load_inc_index()

    target_competitions = get_target_competitions(
        index_data
    )

    outputs = []
    timings = []

    total = len(target_competitions)

    for index, (
        country_id,
        country_name,
        competition_id,
    ) in enumerate(
        target_competitions,
        start=1,
    ):
        if progress_callback is not None:
            progress_callback(
                index,
                total,
                int(country_id),
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

        club_stats = collect_competition_club_stats(
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
            club_stats,
        )

        outputs.append(
            {
                "country_id": int(country_id),
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
                "country_id": int(country_id),
                "country_name": country_name,
                "elapsed_seconds": elapsed_seconds,
            }
        )

    return (
        outputs,
        timings,
        total,
        total,
        TARGET_SEASON,
    )
