import json
from pathlib import Path


ROOT_DIR = Path(__file__).resolve().parent.parent
INC_HISTORY_DIR = ROOT_DIR / "data" / "INC"


def find_inc_history_dir() -> Path:
    if INC_HISTORY_DIR.is_dir():
        return INC_HISTORY_DIR

    raise FileNotFoundError(
        "Could not find data/INC/"
    )


def load_inc_history() -> dict:
    history_dir = find_inc_history_dir()

    paths = sorted(
        history_dir.glob(
            "inc_*_all_seasons.json"
        )
    )

    if not paths:
        raise FileNotFoundError(
            (
                "No inc_*_all_seasons.json files "
                f"found in {history_dir}"
            )
        )

    countries = {}
    last_updated_season = None

    for path in paths:
        with path.open(
            "r",
            encoding="utf-8",
        ) as file:
            data = json.load(file)

        file_last_updated = data.get(
            "last_updated_season"
        )

        try:
            file_last_updated = int(
                file_last_updated
            )
        except (TypeError, ValueError):
            file_last_updated = None

        if (
            file_last_updated is not None
            and (
                last_updated_season is None
                or file_last_updated
                > last_updated_season
            )
        ):
            last_updated_season = (
                file_last_updated
            )

        file_countries = data.get(
            "countries"
        )

        if not isinstance(
            file_countries,
            dict,
        ):
            continue

        for (
            country_id,
            country_data,
        ) in file_countries.items():
            if not isinstance(
                country_data,
                dict,
            ):
                continue

            country_name = (
                country_data.get("name")
            )

            competitions = (
                country_data.get(
                    "competitions"
                )
            )

            if (
                not isinstance(
                    country_name,
                    str,
                )
                or not country_name
                or not isinstance(
                    competitions,
                    dict,
                )
            ):
                continue

            if country_id not in countries:
                countries[country_id] = {
                    "name": country_name,
                    "competitions": {},
                }

            countries[country_id][
                "competitions"
            ].update(
                competitions
            )

    if not countries:
        raise ValueError(
            "No valid INC country data was found"
        )

    return {
        "last_updated_season": (
            last_updated_season
        ),
        "countries": countries,
    }


def get_country_options(
    history: dict,
) -> list[str]:
    countries = history["countries"]

    return sorted(
        countries,
        key=lambda country_id: (
            countries[country_id][
                "name"
            ].lower(),
            int(country_id),
        ),
    )


def get_available_seasons(
    history: dict,
    country_id: str | None,
) -> list[int]:
    countries = history["countries"]

    seasons = set()

    if country_id is None:
        selected_countries = (
            countries.values()
        )
    else:
        selected_countries = [
            countries[country_id]
        ]

    for country_data in selected_countries:
        for season_value in (
            country_data[
                "competitions"
            ]
        ):
            try:
                season = int(
                    season_value
                )
            except (
                TypeError,
                ValueError,
            ):
                continue

            seasons.add(season)

    return sorted(
        seasons,
        reverse=True,
    )


def is_no_club(
    club: dict,
) -> bool:
    return (
        club.get("club_id") is None
        and club.get("name") == "No Club"
    )


def make_club_key(
    club: dict,
) -> tuple:
    club_id = club.get("club_id")

    if club_id is not None:
        return (
            "id",
            club_id,
        )

    return (
        "name",
        club.get("name", ""),
    )


def aggregate_medals(
    history: dict,
    country_id: str | None,
    first_season: int,
    last_season: int,
) -> list[dict]:
    minimum_season = min(
        first_season,
        last_season,
    )

    maximum_season = max(
        first_season,
        last_season,
    )

    countries = history["countries"]

    if country_id is None:
        selected_country_ids = list(
            countries
        )
    else:
        selected_country_ids = [
            country_id
        ]

    aggregated = {}

    for current_country_id in (
        selected_country_ids
    ):
        country_data = countries[
            current_country_id
        ]

        for (
            season_value,
            competition_data,
        ) in country_data[
            "competitions"
        ].items():
            try:
                season = int(
                    season_value
                )
            except (
                TypeError,
                ValueError,
            ):
                continue

            if not (
                minimum_season
                <= season
                <= maximum_season
            ):
                continue

            if not isinstance(
                competition_data,
                dict,
            ):
                continue

            clubs = competition_data.get(
                "clubs",
                [],
            )

            if not isinstance(
                clubs,
                list,
            ):
                continue

            for club in clubs:
                if not isinstance(
                    club,
                    dict,
                ):
                    continue

                key = make_club_key(
                    club
                )

                if key not in aggregated:
                    aggregated[key] = {
                        "club_id": (
                            club.get(
                                "club_id"
                            )
                        ),
                        "name": (
                            club.get(
                                "name",
                                "",
                            )
                        ),
                        "gold": 0,
                        "silver": 0,
                        "bronze": 0,
                    }

                aggregated[key]["gold"] += int(
                    club.get(
                        "gold",
                        0,
                    )
                    or 0
                )

                aggregated[key]["silver"] += int(
                    club.get(
                        "silver",
                        0,
                    )
                    or 0
                )

                aggregated[key]["bronze"] += int(
                    club.get(
                        "bronze",
                        0,
                    )
                    or 0
                )

    regular_clubs = []
    no_club = []

    for club in aggregated.values():
        if (
            club["gold"]
            + club["silver"]
            + club["bronze"]
            <= 0
        ):
            continue

        if is_no_club(club):
            no_club.append(club)
        else:
            regular_clubs.append(club)

    regular_clubs.sort(
        key=lambda club: (
            -club["gold"],
            -club["silver"],
            -club["bronze"],
            club["name"].lower(),
            (
                club["club_id"]
                if club["club_id"] is not None
                else -1
            ),
        )
    )

    no_club.sort(
        key=lambda club: (
            -club["gold"],
            -club["silver"],
            -club["bronze"],
        )
    )

    return (
        regular_clubs
        + no_club
    )
