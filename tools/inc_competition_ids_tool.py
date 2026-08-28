import json
import re
from urllib.parse import parse_qs, urlparse

import requests
from bs4 import BeautifulSoup


WORLD_URL = "https://maxithlon.com/geo/geo_mondo.php"
COUNTRY_COMPETITIONS_URL = (
    "https://maxithlon.com/geo/geo_competitions.php?n={country_id}"
)

INC_PATTERN = re.compile(
    r"^(\d+)\s*-\s*Individual National Championship$"
)


def fetch_html(
    session: requests.Session,
    url: str,
) -> str:
    response = session.get(url)
    response.raise_for_status()
    return response.text


def extract_country_id(href: str) -> int | None:
    parsed = urlparse(href)
    query = parse_qs(parsed.query)

    country_values = query.get("n")
    if not country_values:
        return None

    country_id = country_values[0]

    if not country_id.isdigit():
        return None

    return int(country_id)


def extract_countries(html: str) -> list[tuple[int, str]]:
    soup = BeautifulSoup(html, "html.parser")

    countries: dict[int, str] = {}

    for link in soup.find_all(
        "a",
        href=lambda href: href and "geo_nazione.php?n=" in href,
    ):
        country_id = extract_country_id(link["href"])
        if country_id is None:
            continue

        country_name = link.get_text(" ", strip=True)
        if not country_name:
            continue

        countries[country_id] = country_name

    if not countries:
        raise ValueError("No countries found")

    return sorted(
        countries.items(),
        key=lambda item: item[1].casefold(),
    )


def extract_inc_competitions(html: str) -> dict[int, int]:
    soup = BeautifulSoup(html, "html.parser")

    competition_select = soup.find("select", attrs={"name": "m"})
    if competition_select is None:
        return {}

    competitions: dict[int, int] = {}

    for option in competition_select.find_all("option"):
        label = option.get_text(" ", strip=True)
        match = INC_PATTERN.match(label)

        if match is None:
            continue

        competition_id = option.get("value", "").strip()
        if not competition_id.isdigit():
            continue

        season = int(match.group(1))
        competitions[season] = int(competition_id)

    return competitions


def build_inc_competitions_data(
    session: requests.Session,
    progress_callback=None,
) -> dict:
    world_html = fetch_html(session, WORLD_URL)
    countries = extract_countries(world_html)

    result_countries: dict[str, dict] = {}
    latest_season = 0

    total_countries = len(countries)

    for index, (country_id, country_name) in enumerate(
        countries,
        start=1,
    ):
        if progress_callback is not None:
            progress_callback(
                index,
                total_countries,
                country_id,
                country_name,
            )

        url = COUNTRY_COMPETITIONS_URL.format(
            country_id=country_id
        )
        country_html = fetch_html(session, url)

        competitions = extract_inc_competitions(country_html)

        if not competitions:
            continue

        latest_season = max(
            latest_season,
            max(competitions),
        )

        result_countries[str(country_id)] = {
            "name": country_name,
            "competitions": {
                str(season): competitions[season]
                for season in sorted(
                    competitions,
                    reverse=True,
                )
            },
        }

    if not result_countries:
        raise ValueError(
            "No Individual National Championships found"
        )

    return {
        "last_updated_season": latest_season,
        "countries": result_countries,
    }


def get_inc_competitions_json(
    session: requests.Session,
    progress_callback=None,
) -> tuple[bytes, int, int, int]:
    data = build_inc_competitions_data(
        session,
        progress_callback=progress_callback,
    )

    json_data = json.dumps(
        data,
        ensure_ascii=False,
        indent=2,
    ).encode("utf-8")

    country_count = len(data["countries"])
    competition_count = sum(
        len(country["competitions"])
        for country in data["countries"].values()
    )

    return (
        json_data,
        country_count,
        competition_count,
        data["last_updated_season"],
    )
