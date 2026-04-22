import requests
from bs4 import BeautifulSoup


WORLD_FIRST_PLACE = {
    "Olympic Games": 80000,
    "World championship": 80000,
    "World U21 Championships": 40000,
    "World Junior Championships": 40000,
    "World Master Championships": 40000,
}

WORLD_PAID_PLACES = {
    "Olympic Games": 30,
    "World championship": 30,
    "World U21 Championships": 25,
    "World Junior Championships": 25,
    "World Master Championships": 25,
}

CONTINENTAL_FIRST_PLACE = {
    "Continental Championships": {
        "Europe": 64098,
        "Asia - Africa - Pacific": 40752,
        "America": 43120,
    },
    "Continental U21 Championships": {
        "Europe": 25865,
        "Asia - Africa - Pacific": 5113,
        "America": 7218,
    },
    "Continental Junior Championships": {
        "Europe": 25865,
        "Asia - Africa - Pacific": 5113,
        "America": 7218,
    },
    "Continental Master Championships": {
        "Europe": 25865,
        "Asia - Africa - Pacific": 5113,
        "America": 7218,
    },
}

CONTINENTAL_PAID_PLACES = {
    "Continental Championships": 20,
    "Continental U21 Championships": 15,
    "Continental Junior Championships": 15,
    "Continental Master Championships": 15,
}


def fetch_ind_awards_html(session, nation_id: int) -> str:
    resp = session.post(
        "https://maxithlon.com/common/ajax/awards_ind.php",
        data=[
            ("comp[]", 16),
            ("comp[]", 10),
            ("comp[]", 18),
            ("comp[]", 14),
            ("comp[]", 17),
            ("comp[]", 8),
            ("nazione", nation_id),
        ],
    )
    resp.raise_for_status()
    return resp.text


def _build_awards_rows(html: str):
    soup = BeautifulSoup(f"<table>{html}</table>", "html.parser")
    rows = soup.find_all("tr")
    if not rows:
        raise ValueError("Awards rows not found")
    return rows


def _extract_continental_area(comp_name: str) -> str:
    if "Europe" in comp_name:
        return "Europe"
    if "America" in comp_name:
        return "America"
    return "Asia - Africa - Pacific"


def extract_individual_national_first(html: str) -> int:
    rows = _build_awards_rows(html)

    for tr in rows:
        tds = tr.find_all("td")
        if not tds:
            continue

        if tds[0].get_text(strip=True) == "1":
            if len(tds) <= 6:
                raise ValueError("Individual National Championship column not found")

            raw = tds[6].get_text(strip=True)
            raw = raw.replace(".", "").replace(",", "").strip()

            if not raw:
                raise ValueError("First place value missing")

            return int(raw)

    raise ValueError("First place row not found")


def extract_individual_national_paid_places(html: str) -> int:
    rows = _build_awards_rows(html)
    paid_places = 0

    for tr in rows:
        tds = tr.find_all("td")
        if not tds:
            continue

        place_text = tds[0].get_text(strip=True)
        if not place_text.isdigit():
            continue

        if len(tds) <= 6:
            continue

        raw = tds[6].get_text(strip=True)
        raw = raw.replace(".", "").replace(",", "").strip()

        if raw:
            paid_places = int(place_text)

    if paid_places <= 0:
        raise ValueError("Paid places not found")

    return paid_places


def get_first_place_award_for_type(
    session: requests.Session,
    nation_id: int,
    comp_type: str,
    comp_name: str,
) -> int:
    if comp_type == "Individual National Championship":
        html = fetch_ind_awards_html(session, nation_id)
        return extract_individual_national_first(html)

    if comp_type in WORLD_FIRST_PLACE:
        return WORLD_FIRST_PLACE[comp_type]

    if comp_type in CONTINENTAL_FIRST_PLACE:
        area = _extract_continental_area(comp_name)
        return CONTINENTAL_FIRST_PLACE[comp_type][area]

    raise ValueError("First place income not implemented for this competition type")


def get_paid_places_for_type(
    session: requests.Session,
    nation_id: int,
    comp_type: str,
    comp_name: str,
) -> int:
    if comp_type == "Individual National Championship":
        html = fetch_ind_awards_html(session, nation_id)
        return extract_individual_national_paid_places(html)

    if comp_type in WORLD_PAID_PLACES:
        return WORLD_PAID_PLACES[comp_type]

    if comp_type in CONTINENTAL_PAID_PLACES:
        return CONTINENTAL_PAID_PLACES[comp_type]

    raise ValueError("Paid places not implemented for this competition type")


def extract_nation_ids_from_html(html: str) -> list[int]:
    soup = BeautifulSoup(html, "html.parser")

    select = soup.find("select", id="nazione_ind")
    if not select:
        raise ValueError("Nation selector not found")

    nation_ids = []

    for option in select.find_all("option"):
        value = option.get("value")
        if value and value.isdigit():
            nation_ids.append(int(value))

    return nation_ids


def build_individual_national_max_map(
    session: requests.Session,
    source_html: str,
) -> dict[int, int]:
    nation_ids = extract_nation_ids_from_html(source_html)

    result = {}

    for nation_id in nation_ids:
        html = fetch_ind_awards_html(session, nation_id)
        result[nation_id] = extract_individual_national_first(html)

    return result
