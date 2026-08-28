import json
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

TARGET_COUNTRY_ID = 1
TARGET_SEASON = 107


def find_inc_index_path() -> Path:
    for path in INC_INDEX_PATHS:
        if path.exists():
            return path

    raise FileNotFoundError(
        "Could not find "
        "Data/inc_competitions.json "
        "or data/inc_competitions.json"
    )


def load_inc_index() -> dict:
    path = find_inc_index_path()

    with path.open(
        "r",
        encoding="utf-8",
    ) as file:
        data = json.load(file)

    if "countries" not in data:
        raise ValueError(
            "INC competition index "
            "has no countries"
        )

    return data


def get_target_competition(
    index_data: dict,
) -> tuple[str, str, int]:
    country_id = str(
        TARGET_COUNTRY_ID
    )

    country_data = (
        index_data["countries"].get(
            country_id
        )
    )

    if country_data is None:
        raise ValueError(
            f"Country ID "
            f"{TARGET_COUNTRY_ID} "
            f"not found"
        )

    season_key = str(
        TARGET_SEASON
    )

    competition_id = (
        country_data[
            "competitions"
        ].get(
            season_key
        )
    )

    if competition_id is None:
        raise ValueError(
            f"No season "
            f"{TARGET_SEASON} "
            f"INC found for "
            f"country ID "
            f"{TARGET_COUNTRY_ID}"
        )

    return (
        country_id,
        country_data["name"],
        int(competition_id),
    )


def build_inc_history_data(
    session: requests.Session,
    progress_callback=None,
) -> tuple[dict, int, int]:
    index_data = load_inc_index()

    (
        country_id,
        country_name,
        competition_id,
    ) = get_target_competition(
        index_data
    )

    if progress_callback is not None:
        progress_callback(
            1,
            1,
            TARGET_COUNTRY_ID,
            (
                f"{country_name} - "
                f"season "
                f"{TARGET_SEASON}"
            ),
        )

    competition_html = (
        fetch_competition_details_html(
            session,
            competition_id,
        )
    )

    validate_official_individual_competition(
        competition_html
    )

    club_stats = (
        collect_competition_club_stats(
            session,
            competition_html,
        )
    )

    output = {
        "last_updated_season": (
            TARGET_SEASON
        ),
        "countries": {
            country_id: {
                "name": country_name,
                "competitions": {
                    str(
                        TARGET_SEASON
                    ): {
                        "competition_id": (
                            competition_id
                        ),
                        "clubs": club_stats,
                    }
                },
            }
        },
    }

    return (
        output,
        1,
        1,
    )


def get_inc_competitions_json(
    session: requests.Session,
    progress_callback=None,
) -> tuple[bytes, int, int, int]:
    (
        history_data,
        country_count,
        competition_count,
    ) = build_inc_history_data(
        session,
        progress_callback=(
            progress_callback
        ),
    )

    json_data = json.dumps(
        history_data,
        ensure_ascii=False,
        indent=2,
    ).encode(
        "utf-8"
    )

    return (
        json_data,
        country_count,
        competition_count,
        TARGET_SEASON,
    )
