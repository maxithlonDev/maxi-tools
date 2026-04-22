import io
import csv
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

    for i, line in enumerate(lines):
        if "Competition type:" in line:
            after = line.split("Competition type:", 1)[1].strip()
            if after:
                return after
            if i + 1 < len(lines):
                return lines[i + 1].strip()
            break

    raise ValueError("Competition type not found")


def extract_competition_name(html: str) -> str:
    soup = BeautifulSoup(html, "html.parser")

    h3 = soup.find("h3")
    if not h3:
        return "Unknown Competition"

    text = h3.get_text(" ", strip=True)

    if "[MANID=" in text:
        text = text.split("[MANID=", 1)[0].strip()

    return text


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
    if not h3:
        raise ValueError("Event name not found")

    text = h3.get_text(" ", strip=True)

    if text.startswith("Results - "):
        text = text[len("Results - "):]

    if text.endswith(" - Maxithlon"):
        text = text[:-len(" - Maxithlon")]

    return text.strip()


def validate_official_individual_competition(html: str) -> None:
    comp_type = extract_competition_type(html)

    if comp_type not in VALID_OFFICIAL_TYPES:
        raise ValueError("Not an official individual competition")


def get_first_place_income(
    session: requests.Session,
    html: str,
) -> int:
    comp_type = extract_competition_type(html)
    nation_id = extract_competition_nation_id(html)
    return get_first_place_award_for_type(session, nation_id, comp_type)


def get_paid_places(
    session: requests.Session,
    html: str,
) -> int:
    comp_type = extract_competition_type(html)
    nation_id = extract_competition_nation_id(html)
    return get_paid_places_for_type(session, nation_id, comp_type)


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


def get_place_income(place: int, first_place_income: int) -> int:
    if place <= 0:
        return 0
    if place == 1:
        return first_place_income
    return int(round(first_place_income * 1.25 / place))


def extract_event_incomes_by_club(
    html: str,
    paid_places: int,
    first_place_income: int,
) -> dict[str, int]:
    soup = BeautifulSoup(html, "html.parser")
    result: dict[str, int] = {}

    event_name = extract_event_name(html)
    is_relay = "Relay" in event_name

    rows = soup.find_all("tr")
    place = 0

    for tr in rows:
        tds = tr.find_all("td")
        if not tds:
            continue

        if is_relay:
            team_link = tr.find(
                "a",
                href=lambda x: x and "staffetta_one.php?sid=" in x,
            )
            if not team_link:
                continue

            place += 1
            if place > paid_places:
                break

            team_name = team_link.get_text(strip=True)
            if not team_name:
                continue

            club_name = team_name
            if " 4x" in club_name:
                club_name = club_name.split(" 4x", 1)[0].strip()

            income = get_place_income(place, first_place_income)
            result[club_name] = result.get(club_name, 0) + income
        else:
            club_link = tr.find(
                "a",
                href=lambda x: x and "dettagli_societa.php?u=" in x,
            )
            if not club_link:
                continue

            place += 1
            if place > paid_places:
                break

            club_name = club_link.get_text(strip=True)
            if not club_name:
                continue

            income = get_place_income(place, first_place_income)
            result[club_name] = result.get(club_name, 0) + income

    return result


def collect_competition_incomes_by_club(
    session: requests.Session,
    competition_html: str,
    progress_callback=None,
) -> dict[str, int]:
    first_place_income = get_first_place_income(session, competition_html)
    paid_places = get_paid_places(session, competition_html)
    event_ids = build_relevant_event_ids(competition_html)

    total_by_club: dict[str, int] = {}
    total_events = len(event_ids)

    for idx, event_id in enumerate(event_ids, start=1):
        if progress_callback is not None:
            progress_callback(idx, total_events, event_id)

        print(f"parsing event id {event_id}")
        event_html = fetch_event_result_html(session, event_id)
        event_incomes = extract_event_incomes_by_club(
            event_html,
            paid_places,
            first_place_income,
        )

        for club_name, income in event_incomes.items():
            total_by_club[club_name] = (
                total_by_club.get(club_name, 0) + income
            )

    return total_by_club


def build_income_csv(incomes_by_club: dict[str, int]) -> bytes:
    buf = io.StringIO()
    writer = csv.writer(buf)
    writer.writerow(["club", "income"])

    for club_name, income in sorted(
        incomes_by_club.items(),
        key=lambda x: (-x[1], x[0]),
    ):
        writer.writerow([club_name, income])

    return buf.getvalue().encode("utf-8")


def get_official_comp_income_csv(
    session: requests.Session,
    comp_id: int,
    progress_callback=None,
) -> tuple[bytes, str]:
    html = fetch_competition_details_html(session, comp_id)
    validate_official_individual_competition(html)
    comp_name = extract_competition_name(html)
    incomes_by_club = collect_competition_incomes_by_club(
        session,
        html,
        progress_callback=progress_callback,
    )
    csv_data = build_income_csv(incomes_by_club)
    return csv_data, comp_name
