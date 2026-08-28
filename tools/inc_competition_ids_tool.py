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

    with path.open(
        "r",
        encoding="utf-8",
    ) as file:
        data = json.load(file)

    if "countries" not in data:
        raise ValueError(
            "INC competition index has no countries"
        )

    return data


def build_competition_queue(
    index_data: dict,
) -> list[tuple[str, str, int, int]]:
    queue = []

    for country_id, country_data in index_data["countries"].items():
        country_name = country_data["name"]

        for season_str, competition_id in country_data[
            "competitions"
        ].items():
            queue.append(
                (
                    str(country_id),
                    country_name,
                    int(season_str),
                    int(competition_id),
                )
            )

    queue.sort(
        key=lambda item: (
            item[1].casefold(),
            -item[2],
        )
    )

    return queue


def build_inc_history_data(
    session: requests.Session,
    progress_callback=None,
) -> tuple[dict, int, int]:
    index_data = load_inc_index()
    competition_queue = build_competition_queue(
        index_data
    )

    output = {
        "last_updated_season": index_data.get(
            "last_updated_season"
        ),
        "countries": {},
    }

    errors = []

    total_competitions = len(competition_queue)
    successful_competitions = 0
    successful_country_ids = set()

    for (
        index,
        (
            country_id,
            country_name,
            season,
            competition_id,
        ),
    ) in enumerate(
        competition_queue,
        start=1,
    ):
        if progress_callback is not None:
            progress_callback(
                index,
                total_competitions,
                int(country_id),
                f"{country_name} - season {season}",
            )

        country_output = output["countries"].setdefault(
            country_id,
            {
                "name": country_name,
                "competitions": {},
            },
        )

        try:
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

            country_output["competitions"][str(season)] = {
                "competition_id": competition_id,
                "clubs": club_stats,
            }

            successful_competitions += 1
            successful_country_ids.add(country_id)

        except Exception as error:
            errors.append(
                {
                    "country_id": int(country_id),
                    "country_name": country_name,
                    "season": season,
                    "competition_id": competition_id,
                    "error": str(error),
                }
            )

    if errors:
        output["errors"] = errors

    return (
        output,
        len(successful_country_ids),
        successful_competitions,
    )


def get_inc_competitions_json(
    session: requests.Session,
    progress_callback=None,
) -> tuple[bytes, int, int, int]:
    index_data = load_inc_index()

    history_data, country_count, competition_count = (
        build_inc_history_data(
            session,
            progress_callback=progress_callback,
        )
    )

    latest_season = index_data.get(
        "last_updated_season"
    )

    if latest_season is None:
        seasons = [
            int(season)
            for country in index_data["countries"].values()
            for season in country["competitions"]
        ]

        if not seasons:
            raise ValueError(
                "No INC competitions found in index"
            )

        latest_season = max(seasons)

    json_data = json.dumps(
        history_data,
        ensure_ascii=False,
        indent=2,
    ).encode("utf-8")

    return (
        json_data,
        country_count,
        competition_count,
        int(latest_season),
    )
