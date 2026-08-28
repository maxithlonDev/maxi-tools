import csv
import io

import requests
from bs4 import BeautifulSoup

from tools.competition_income_nations_tool import (
    get_first_place_award_for_type,
    get_paid_places_for_type,
)


VALID_OFFICIAL_TYPES = {
    "Individual National Championship",
    "World championship",
    "Olympic Games",
    "World Junior Championships",
    "World U21 Championships",
    "World Master Championships",
    "Continental Championships",
    "Continental Junior Championships",
    "Continental U21 Championships",
    "Continental Master Championships",
}

RELEVANT_EVENT_OFFSETS = list(range(48)) + [53, 59, 67, 78]

NO_CLUB_NAME = "No Club"


def fetch_competition_details_html(
    session: requests.Session,
    comp_id: int,
) -> str:
    details_url = (
        f"https://maxithlon.com/manifestazioni/man_dettagli.php?m={comp_id}"
    )

    resp = session.get(details_url)
    resp.raise_for_status()
    return resp.text


def fetch_event_result_html(
    session: requests.Session,
    event_id: int,
) -> str:
    resp = session.get(
        f"https://maxithlon.com/manifestazioni/risultati_gara.php?e={event_id}"
    )
    resp.raise_for_status()
    return resp.text


def extract_competition_type(html: str) -> str:
    soup = BeautifulSoup(html, "html.parser")
    page_text = soup.get_text("\n", strip=True)
    lines = page_text.splitlines()

    labels = (
        "Competition type:",
        "Type of competition:",
    )

    for i, line in enumerate(lines):
        for label in labels:
            if label not in line:
                continue

            after = line.split(label, 1)[1].strip()
            if after:
                return after

            if i + 1 < len(lines):
                return lines[i + 1].strip()

    raise ValueError("Competition type not found")


def extract_competition_name(html: str) -> str:
    soup = BeautifulSoup(html, "html.parser")
    h3 = soup.find("h3")

    if h3:
        text = h3.get_text(" ", strip=True)

        if "[MANID=" in text:
            text = text.split("[MANID=", 1)[0].strip()

        if text:
            return text

    for tr in soup.find_all("tr"):
        tds = tr.find_all("td")
        if len(tds) < 2:
            continue

        label = tds[0].get_text(" ", strip=True)
        if label not in {"Competition:", "Competitions:"}:
            continue

        name = tds[1].get_text(" ", strip=True)
        if name:
            return name

    return "Unknown Competition"


def extract_competition_nation_id(html: str) -> int:
    soup = BeautifulSoup(html, "html.parser")

    nation_link = soup.find(
        "a",
        href=lambda x: x and "geo_nazione.php?n=" in x,
    )

    if not nation_link:
        raise ValueError("Competition nation not found")

    href = nation_link["href"]
    nation_id = href.split("geo_nazione.php?n=", 1)[1].split("&", 1)[0]

    if not nation_id.isdigit():
        raise ValueError("Invalid competition nation")

    return int(nation_id)


def extract_event_name(html: str) -> str:
    soup = BeautifulSoup(html, "html.parser")

    h3 = soup.find("h3")
    if h3:
        text = h3.get_text(" ", strip=True)

        if text.startswith("Results - "):
            text = text[len("Results - "):]

        if text.endswith(" - Maxithlon"):
            text = text[:-len(" - Maxithlon")]

        if text:
            return text.strip()

    title = soup.find("title")
    if title:
        text = title.get_text(" ", strip=True)

        if text.startswith("Results - "):
            text = text[len("Results - "):]

        if text.endswith(" - Maxithlon"):
            text = text[:-len(" - Maxithlon")]

        if text:
            return text.strip()

    raise ValueError("Event name not found")


def validate_official_individual_competition(html: str) -> None:
    comp_type = extract_competition_type(html)

    if comp_type not in VALID_OFFICIAL_TYPES:
        raise ValueError("Not an official individual competition")


def get_first_place_income(
    session: requests.Session,
    html: str,
) -> int:
    comp_type = extract_competition_type(html)
    comp_name = extract_competition_name(html)
    nation_id = extract_competition_nation_id(html)

    return get_first_place_award_for_type(
        session,
        nation_id,
        comp_type,
        comp_name,
    )


def get_paid_places(
    session: requests.Session,
    html: str,
) -> int:
    comp_type = extract_competition_type(html)
    comp_name = extract_competition_name(html)
    nation_id = extract_competition_nation_id(html)

    return get_paid_places_for_type(
        session,
        nation_id,
        comp_type,
        comp_name,
    )


def extract_first_event_id(html: str) -> int:
    soup = BeautifulSoup(html, "html.parser")

    event_link = soup.find(
        "a",
        href=lambda x: x and "risultati_gara.php?e=" in x,
    )

    if not event_link:
        raise ValueError("First event link not found")

    href = event_link["href"]
    event_id = href.split("risultati_gara.php?e=", 1)[1].split("&", 1)[0]

    if not event_id.isdigit():
        raise ValueError("Invalid first event id")

    return int(event_id)


def build_relevant_event_ids(html: str) -> list[int]:
    first_event_id = extract_first_event_id(html)
    return [first_event_id + offset for offset in RELEVANT_EVENT_OFFSETS]


def get_place_income(
    place: int,
    first_place_income: int,
) -> int:
    if place <= 0:
        return 0

    if place == 1:
        return first_place_income

    return int(round(first_place_income * 1.25 / place))


def extract_club_id(href: str | None) -> int | None:
    if not href or "dettagli_societa.php?u=" not in href:
        return None

    club_id = href.split("dettagli_societa.php?u=", 1)[1].split("&", 1)[0]

    if not club_id.isdigit():
        return None

    return int(club_id)


def extract_place(tr) -> int | None:
    tds = tr.find_all("td")
    if not tds:
        return None

    first_cell = tds[0]

    medal_image = first_cell.find("img")
    if medal_image is not None:
        alt = medal_image.get("alt", "").strip()
        if alt.isdigit():
            place = int(alt)
            return place if place > 0 else None

    text = first_cell.get_text(" ", strip=True)

    if not text.isdigit():
        return None

    place = int(text)
    return place if place > 0 else None


def find_results_table(soup: BeautifulSoup):
    for table in soup.find_all("table"):
        classes = table.get("class", [])

        if "results" not in classes:
            continue

        header_texts = [
            th.get_text(" ", strip=True).casefold()
            for th in table.find_all("th")
        ]

        if "club" in header_texts:
            return table

    return None


def find_club_column_index(table) -> int | None:
    header_row = table.find("thead")

    if header_row is None:
        return None

    headers = header_row.find_all("th")

    for index, th in enumerate(headers):
        if th.get_text(" ", strip=True).casefold() == "club":
            return index

    return None


def extract_individual_club(
    tr,
    club_column_index: int,
) -> tuple[int | None, str]:
    tds = tr.find_all("td")

    if club_column_index >= len(tds):
        return None, NO_CLUB_NAME

    club_cell = tds[club_column_index]

    club_link = club_cell.find(
        "a",
        href=lambda x: x and "dettagli_societa.php?u=" in x,
    )

    if club_link is not None:
        club_name = club_link.get_text(" ", strip=True)
        club_id = extract_club_id(club_link.get("href"))

        if club_name:
            return club_id, club_name

    club_name = club_cell.get_text(" ", strip=True)

    if not club_name:
        return None, NO_CLUB_NAME

    return None, club_name


def extract_relay_club(
    tr,
    club_column_index: int | None,
) -> tuple[int | None, str]:
    club_link = tr.find(
        "a",
        href=lambda x: x and "dettagli_societa.php?u=" in x,
    )

    if club_link is not None:
        club_name = club_link.get_text(" ", strip=True)
        club_id = extract_club_id(club_link.get("href"))

        if club_name:
            return club_id, club_name

    team_link = tr.find(
        "a",
        href=lambda x: x and "staffetta_one.php?sid=" in x,
    )

    if team_link is not None:
        team_name = team_link.get_text(" ", strip=True)

        if " 4x" in team_name:
            team_name = team_name.split(" 4x", 1)[0].strip()

        if team_name:
            return None, team_name

    if club_column_index is not None:
        tds = tr.find_all("td")

        if club_column_index < len(tds):
            club_name = tds[club_column_index].get_text(" ", strip=True)

            if " 4x" in club_name:
                club_name = club_name.split(" 4x", 1)[0].strip()

            if club_name:
                return None, club_name

    return None, NO_CLUB_NAME


def extract_event_club_results(
    html: str,
    paid_places: int,
    first_place_income: int,
) -> list[dict]:
    soup = BeautifulSoup(html, "html.parser")
    table = find_results_table(soup)

    if table is None:
        raise ValueError("Event results table not found")

    event_name = extract_event_name(html)
    is_relay = "Relay" in event_name

    club_column_index = find_club_column_index(table)

    if not is_relay and club_column_index is None:
        raise ValueError("Club column not found")

    results = []

    for tr in table.find_all("tr"):
        place = extract_place(tr)

        if place is None:
            continue

        if place > paid_places:
            continue

        if is_relay:
            club_id, club_name = extract_relay_club(
                tr,
                club_column_index,
            )
        else:
            club_id, club_name = extract_individual_club(
                tr,
                club_column_index,
            )

        results.append(
            {
                "club_id": club_id,
                "name": club_name,
                "place": place,
                "income": get_place_income(
                    place,
                    first_place_income,
                ),
            }
        )

    return results


def add_club_result(
    club_stats: dict,
    club_id: int | None,
    club_name: str,
    place: int,
    income: int,
) -> None:
    if club_id is not None:
        key = ("id", club_id)

        name_key = ("name", club_name)
        existing_name_stats = club_stats.pop(name_key, None)

        if key not in club_stats:
            club_stats[key] = {
                "club_id": club_id,
                "name": club_name,
                "income": 0,
                "gold": 0,
                "silver": 0,
                "bronze": 0,
            }

        stats = club_stats[key]

        if existing_name_stats is not None:
            stats["income"] += existing_name_stats["income"]
            stats["gold"] += existing_name_stats["gold"]
            stats["silver"] += existing_name_stats["silver"]
            stats["bronze"] += existing_name_stats["bronze"]

    else:
        matching_id_key = None

        for existing_key, existing_stats in club_stats.items():
            if (
                existing_key[0] == "id"
                and existing_stats["name"] == club_name
            ):
                matching_id_key = existing_key
                break

        if matching_id_key is not None:
            key = matching_id_key
        else:
            key = ("name", club_name)

            if key not in club_stats:
                club_stats[key] = {
                    "club_id": None,
                    "name": club_name,
                    "income": 0,
                    "gold": 0,
                    "silver": 0,
                    "bronze": 0,
                }

        stats = club_stats[key]

    stats["income"] += income

    if place == 1:
        stats["gold"] += 1
    elif place == 2:
        stats["silver"] += 1
    elif place == 3:
        stats["bronze"] += 1


def collect_competition_club_stats(
    session: requests.Session,
    competition_html: str,
    progress_callback=None,
) -> list[dict]:
    first_place_income = get_first_place_income(
        session,
        competition_html,
    )

    paid_places = get_paid_places(
        session,
        competition_html,
    )

    event_ids = build_relevant_event_ids(competition_html)

    club_stats: dict = {}
    total_events = len(event_ids)

    for idx, event_id in enumerate(event_ids, start=1):
        if progress_callback is not None:
            progress_callback(idx, total_events, event_id)

        print(f"parsing event id {event_id}")

        event_html = fetch_event_result_html(
            session,
            event_id,
        )

        event_results = extract_event_club_results(
            event_html,
            paid_places,
            first_place_income,
        )

        for result in event_results:
            add_club_result(
                club_stats,
                result["club_id"],
                result["name"],
                result["place"],
                result["income"],
            )

    result = list(club_stats.values())

    result.sort(
        key=lambda club: (
            club["name"] == NO_CLUB_NAME,
            -club["income"],
            club["name"].casefold(),
            club["club_id"] if club["club_id"] is not None else -1,
        )
    )

    return result


def extract_event_incomes_by_club(
    html: str,
    paid_places: int,
    first_place_income: int,
) -> dict[str, int]:
    result: dict[str, int] = {}

    for row in extract_event_club_results(
        html,
        paid_places,
        first_place_income,
    ):
        club_name = row["name"]
        income = row["income"]

        result[club_name] = (
            result.get(club_name, 0) + income
        )

    return result


def collect_competition_incomes_by_club(
    session: requests.Session,
    competition_html: str,
    progress_callback=None,
) -> dict[str, int]:
    stats = collect_competition_club_stats(
        session,
        competition_html,
        progress_callback=progress_callback,
    )

    total_by_club: dict[str, int] = {}

    for club in stats:
        club_name = club["name"]

        total_by_club[club_name] = (
            total_by_club.get(club_name, 0)
            + club["income"]
        )

    return total_by_club


def build_income_csv(
    incomes_by_club: dict[str, int],
) -> bytes:
    buf = io.StringIO()
    writer = csv.writer(buf)

    writer.writerow(["club", "income"])

    rows = sorted(
        incomes_by_club.items(),
        key=lambda item: (
            item[0] == NO_CLUB_NAME,
            -item[1],
            item[0].casefold(),
        ),
    )

    for club_name, income in rows:
        writer.writerow([club_name, income])

    return buf.getvalue().encode("utf-8")


def get_official_comp_income_csv(
    session: requests.Session,
    comp_id: int,
    progress_callback=None,
) -> tuple[bytes, str]:
    html = fetch_competition_details_html(
        session,
        comp_id,
    )

    validate_official_individual_competition(html)

    comp_name = extract_competition_name(html)

    incomes_by_club = collect_competition_incomes_by_club(
        session,
        html,
        progress_callback=progress_callback,
    )

    csv_data = build_income_csv(incomes_by_club)

    return csv_data, comp_name
