import requests
from bs4 import BeautifulSoup


COMP_TYPE_TO_COL_IDX = {
    "Olympic Games": 1,
    "World championship": 2,
    "World U21 Championships": 3,
    "World Junior Championships": 4,
    "World Master Championships": 5,
    "Individual National Championship": 6,
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


def extract_first_place_award(html: str, comp_type: str) -> int:
    if comp_type not in COMP_TYPE_TO_COL_IDX:
        raise ValueError(
            "First place income not implemented for this competition type"
        )

    col_idx = COMP_TYPE_TO_COL_IDX[comp_type]
    rows = _build_awards_rows(html)

    for tr in rows:
        tds = tr.find_all("td")
        if not tds:
            continue

        if tds[0].get_text(strip=True) == "1":
            if len(tds) <= col_idx:
                raise ValueError("Requested awards column not found")

            raw = tds[col_idx].get_text(strip=True)
            raw = raw.replace(".", "").replace(",", "").strip()

            if not raw:
                raise ValueError("First place value missing")

            return int(raw)

    raise ValueError("First place row not found")


def extract_paid_places(html: str, comp_type: str) -> int:
    if comp_type not in COMP_TYPE_TO_COL_IDX:
        raise ValueError(
            "Paid places not implemented for this competition type"
        )

    col_idx = COMP_TYPE_TO_COL_IDX[comp_type]
    rows = _build_awards_rows(html)

    paid_places = 0

    for tr in rows:
        tds = tr.find_all("td")
        if not tds:
            continue

        place_text = tds[0].get_text(strip=True)
        if not place_text.isdigit():
            continue

        if len(tds) <= col_idx:
            continue

        raw = tds[col_idx].get_text(strip=True)
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
) -> int:
    html = fetch_ind_awards_html(session, nation_id)
    return extract_first_place_award(html, comp_type)


def get_paid_places_for_type(
    session: requests.Session,
    nation_id: int,
    comp_type: str,
) -> int:
    html = fetch_ind_awards_html(session, nation_id)
    return extract_paid_places(html, comp_type)


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
        result[nation_id] = get_first_place_award_for_type(
            session,
            nation_id,
            "Individual National Championship",
        )

    return result
