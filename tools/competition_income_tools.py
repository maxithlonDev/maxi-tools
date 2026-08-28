import csv
import io
from urllib.parse import parse_qs, urlparse

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

NO_CLUB_NAME = "No Club"

COMBINED_EVENT_NAMES = {
    "Pentathlon Men",
    "Pentathlon Women",
    "Heptathlon",
    "Decathlon",
}


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
        tds = tr.find_all("td", recursive=False)

        if len(tds) < 2:
            continue

        label = tds[0].get_text(" ", strip=True)

        if label not in {
            "Competition:",
            "Competitions:",
        }:
            continue

        name = tds[1].get_text(" ", strip=True)

        if name:
            return name

    return "Unknown Competition"


def extract_competition_nation_id(html: str) -> int:
    soup = BeautifulSoup(html, "html.parser")

    subh3 = soup.find("div", class_="subh3")

    if subh3 is not None:
        nation_link = subh3.find(
            "a",
            href=lambda href: (
                href
                and "geo_nazione.php?n=" in href
            ),
        )

        if nation_link is not None:
            href = nation_link["href"]
            nation_id = (
                href.split("geo_nazione.php?n=", 1)[1]
                .split("&", 1)[0]
            )

            if nation_id.isdigit():
                return int(nation_id)

    nation_link = soup.find(
        "a",
        href=lambda href: (
            href
            and "geo_nazione.php?n=" in href
        ),
    )

    if nation_link is None:
        raise ValueError("Competition nation not found")

    href = nation_link["href"]

    nation_id = (
        href.split("geo_nazione.php?n=", 1)[1]
        .split("&", 1)[0]
    )

    if not nation_id.isdigit():
        raise ValueError("Invalid competition nation")

    return int(nation_id)


def extract_event_name(html: str) -> str:
    soup = BeautifulSoup(html, "html.parser")

    title = soup.find("title")

    if title is not None:
        text = title.get_text(" ", strip=True)

        if text.startswith("Results - "):
            text = text[len("Results - "):]

        if text.endswith(" - Maxithlon"):
            text = text[:-len(" - Maxithlon")]

        if text:
            return text.strip()

    h3 = soup.find("h3")

    if h3 is not None:
        text = h3.get_text(" ", strip=True)

        if text.startswith("Results - "):
            text = text[len("Results - "):]

        if text.endswith(" - Maxithlon"):
            text = text[:-len(" - Maxithlon")]

        if text:
            return text.strip()

    raise ValueError("Event name not found")


def validate_official_individual_competition(
    html: str,
) -> None:
    comp_type = extract_competition_type(html)

    if comp_type not in VALID_OFFICIAL_TYPES:
        raise ValueError(
            "Not an official individual competition"
        )


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


def extract_event_id(href: str) -> int | None:
    parsed = urlparse(href)
    query = parse_qs(parsed.query)

    event_values = query.get("e")

    if not event_values:
        return None

    event_id = event_values[0]

    if not event_id.isdigit():
        return None

    return int(event_id)


def is_combined_event_component(
    event_name: str,
) -> bool:
    return any(
        event_name.startswith(
            f"{combined_event_name} - "
        )
        for combined_event_name
        in COMBINED_EVENT_NAMES
    )


def extract_competition_events(
    html: str,
) -> list[tuple[int, str]]:
    soup = BeautifulSoup(html, "html.parser")

    events: list[tuple[int, str]] = []
    seen_event_ids = set()

    event_tables = soup.find_all(
        "table",
        class_="man_events",
    )

    for table in event_tables:
        for tr in table.find_all(
            "tr",
            recursive=False,
        ):
            tds = tr.find_all(
                "td",
                recursive=False,
            )

            if len(tds) < 4:
                continue

            event_cell = tds[-1]

            event_link = None

            for link in event_cell.find_all(
                "a",
                recursive=False,
            ):
                href = link.get("href", "")

                if (
                    "risultati_gara.php?e="
                    not in href
                ):
                    continue

                link_text = link.get_text(
                    " ",
                    strip=True,
                )

                if not link_text:
                    continue

                event_link = link
                break

            if event_link is None:
                continue

            event_id = extract_event_id(
                event_link["href"]
            )

            if event_id is None:
                continue

            if event_id in seen_event_ids:
                continue

            event_name = event_link.get_text(
                " ",
                strip=True,
            )

            if not event_name:
                continue

            if is_combined_event_component(
                event_name
            ):
                continue

            seen_event_ids.add(event_id)

            events.append(
                (
                    event_id,
                    event_name,
                )
            )

    if not events:
        raise ValueError(
            "No competition events found"
        )

    return events


def build_relevant_event_ids(
    html: str,
) -> list[int]:
    return [
        event_id
        for event_id, _
        in extract_competition_events(html)
    ]


def get_place_income(
    place: int,
    first_place_income: int,
) -> int:
    if place <= 0:
        return 0

    if place == 1:
        return first_place_income

    return int(
        round(
            first_place_income
            * 1.25
            / place
        )
    )


def extract_club_id(
    href: str | None,
) -> int | None:
    if not href:
        return None

    parsed = urlparse(href)
    query = parse_qs(parsed.query)

    club_values = query.get("u")

    if not club_values:
        return None

    club_id = club_values[0]

    if not club_id.isdigit():
        return None

    return int(club_id)


def find_results_table(
    soup: BeautifulSoup,
):
    for table in soup.find_all(
        "table",
        class_="results",
    ):
        thead = table.find("thead")

        if thead is None:
            continue

        headers = [
            th.get_text(
                " ",
                strip=True,
            ).casefold()
            for th in thead.find_all("th")
        ]

        if (
            "club" in headers
            or "relay" in headers
        ):
            return table

    return None


def get_header_index(
    table,
    header_name: str,
) -> int | None:
    thead = table.find("thead")

    if thead is None:
        return None

    headers = thead.find_all("th")

    for index, th in enumerate(headers):
        if (
            th.get_text(
                " ",
                strip=True,
            ).casefold()
            == header_name.casefold()
        ):
            return index

    return None


def extract_place(tr) -> int | None:
    tds = tr.find_all(
        "td",
        recursive=False,
    )

    if not tds:
        return None

    first_cell = tds[0]

    medal_image = first_cell.find("img")

    if medal_image is not None:
        alt = medal_image.get(
            "alt",
            "",
        ).strip()

        if alt.isdigit():
            place = int(alt)

            if place > 0:
                return place

    text = first_cell.get_text(
        " ",
        strip=True,
    )

    if not text.isdigit():
        return None

    place = int(text)

    if place <= 0:
        return None

    return place


def extract_individual_club(
    tr,
    club_column_index: int,
) -> tuple[int | None, str]:
    tds = tr.find_all(
        "td",
        recursive=False,
    )

    if club_column_index >= len(tds):
        return None, NO_CLUB_NAME

    club_cell = tds[
        club_column_index
    ]

    club_link = club_cell.find(
        "a",
        href=lambda href: (
            href
            and "dettagli_societa.php?u="
            in href
        ),
    )

    if club_link is not None:
        club_name = club_link.get_text(
            " ",
            strip=True,
        )

        if club_name:
            return (
                extract_club_id(
                    club_link.get("href")
                ),
                club_name,
            )

    club_name = club_cell.get_text(
        " ",
        strip=True,
    )

    if not club_name:
        return None, NO_CLUB_NAME

    return None, club_name


def extract_relay_club(
    tr,
    relay_column_index: int,
) -> tuple[int | None, str]:
    tds = tr.find_all(
        "td",
        recursive=False,
    )

    if relay_column_index >= len(tds):
        return None, NO_CLUB_NAME

    relay_cell = tds[
        relay_column_index
    ]

    relay_link = relay_cell.find(
        "a",
        href=lambda href: (
            href
            and "staffetta_one.php?sid="
            in href
        ),
    )

    if relay_link is not None:
        relay_name = relay_link.get_text(
            " ",
            strip=True,
        )
    else:
        relay_name = relay_cell.get_text(
            " ",
            strip=True,
        )

    if not relay_name:
        return None, NO_CLUB_NAME

    if " 4x" in relay_name:
        relay_name = relay_name.split(
            " 4x",
            1,
        )[0].strip()

    if not relay_name:
        return None, NO_CLUB_NAME

    return None, relay_name


def extract_event_club_results(
    html: str,
    paid_places: int,
    first_place_income: int,
) -> list[dict]:
    soup = BeautifulSoup(
        html,
        "html.parser",
    )

    table = find_results_table(soup)

    if table is None:
        event_name = extract_event_name(html)

        raise ValueError(
            f"Event results table not found "
            f"for {event_name}"
        )

    club_column_index = get_header_index(
        table,
        "Club",
    )

    relay_column_index = get_header_index(
        table,
        "Relay",
    )

    if (
        club_column_index is None
        and relay_column_index is None
    ):
        event_name = extract_event_name(html)

        raise ValueError(
            f"Club or relay column not found "
            f"for {event_name}"
        )

    results = []

    rows = table.find_all(
        "tr",
        recursive=False,
    )

    for tr in rows:
        place = extract_place(tr)

        if place is None:
            continue

        if place > paid_places:
            continue

        if relay_column_index is not None:
            club_id, club_name = (
                extract_relay_club(
                    tr,
                    relay_column_index,
                )
            )
        else:
            club_id, club_name = (
                extract_individual_club(
                    tr,
                    club_column_index,
                )
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


def find_matching_id_key(
    club_stats: dict,
    club_name: str,
):
    for key, stats in club_stats.items():
        if key[0] != "id":
            continue

        if stats["name"] == club_name:
            return key

    return None


def add_club_result(
    club_stats: dict,
    club_id: int | None,
    club_name: str,
    place: int,
    income: int,
) -> None:
    if club_id is not None:
        key = (
            "id",
            club_id,
        )

        if key not in club_stats:
            club_stats[key] = {
                "club_id": club_id,
                "name": club_name,
                "income": 0,
                "gold": 0,
                "silver": 0,
                "bronze": 0,
            }

        name_key = (
            "name",
            club_name,
        )

        old_name_stats = club_stats.pop(
            name_key,
            None,
        )

        if old_name_stats is not None:
            club_stats[key]["income"] += (
                old_name_stats["income"]
            )
            club_stats[key]["gold"] += (
                old_name_stats["gold"]
            )
            club_stats[key]["silver"] += (
                old_name_stats["silver"]
            )
            club_stats[key]["bronze"] += (
                old_name_stats["bronze"]
            )

    else:
        matching_id_key = (
            find_matching_id_key(
                club_stats,
                club_name,
            )
        )

        if matching_id_key is not None:
            key = matching_id_key
        else:
            key = (
                "name",
                club_name,
            )

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


def merge_unlinked_clubs_into_linked(
    club_stats: dict,
) -> None:
    name_keys = [
        key
        for key in club_stats
        if key[0] == "name"
        and key[1] != NO_CLUB_NAME
    ]

    for name_key in name_keys:
        if name_key not in club_stats:
            continue

        club_name = name_key[1]

        id_key = find_matching_id_key(
            club_stats,
            club_name,
        )

        if id_key is None:
            continue

        old_stats = club_stats.pop(
            name_key
        )

        target = club_stats[id_key]

        target["income"] += (
            old_stats["income"]
        )
        target["gold"] += (
            old_stats["gold"]
        )
        target["silver"] += (
            old_stats["silver"]
        )
        target["bronze"] += (
            old_stats["bronze"]
        )


def collect_competition_club_stats(
    session: requests.Session,
    competition_html: str,
    progress_callback=None,
) -> list[dict]:
    first_place_income = (
        get_first_place_income(
            session,
            competition_html,
        )
    )

    paid_places = get_paid_places(
        session,
        competition_html,
    )

    events = extract_competition_events(
        competition_html
    )

    club_stats: dict = {}
    total_events = len(events)

    for (
        index,
        (
            event_id,
            event_name,
        ),
    ) in enumerate(
        events,
        start=1,
    ):
        if progress_callback is not None:
            progress_callback(
                index,
                total_events,
                event_id,
            )

        print(
            f"parsing event "
            f"{index}/{total_events}: "
            f"{event_name} "
            f"[{event_id}]"
        )

        try:
            event_html = (
                fetch_event_result_html(
                    session,
                    event_id,
                )
            )

            event_results = (
                extract_event_club_results(
                    event_html,
                    paid_places,
                    first_place_income,
                )
            )
        except Exception as exc:
            raise RuntimeError(
                f"Failed parsing event "
                f"{index}/{total_events}: "
                f"{event_name} "
                f"[EVENTID={event_id}]: "
                f"{exc}"
            ) from exc

        for result in event_results:
            add_club_result(
                club_stats,
                result["club_id"],
                result["name"],
                result["place"],
                result["income"],
            )

    merge_unlinked_clubs_into_linked(
        club_stats
    )

    result = list(
        club_stats.values()
    )

    result.sort(
        key=lambda club: (
            club["name"] == NO_CLUB_NAME,
            -club["income"],
            -club["gold"],
            -club["silver"],
            -club["bronze"],
            club["name"].casefold(),
            (
                club["club_id"]
                if club["club_id"]
                is not None
                else -1
            ),
        )
    )

    return result


def extract_event_incomes_by_club(
    html: str,
    paid_places: int,
    first_place_income: int,
) -> dict[str, int]:
    result: dict[str, int] = {}

    rows = extract_event_club_results(
        html,
        paid_places,
        first_place_income,
    )

    for row in rows:
        club_name = row["name"]

        result[club_name] = (
            result.get(
                club_name,
                0,
            )
            + row["income"]
        )

    return result


def collect_competition_incomes_by_club(
    session: requests.Session,
    competition_html: str,
    progress_callback=None,
) -> dict[str, int]:
    club_stats = (
        collect_competition_club_stats(
            session,
            competition_html,
            progress_callback=(
                progress_callback
            ),
        )
    )

    return {
        club["name"]: club["income"]
        for club in club_stats
    }


def build_income_csv(
    incomes_by_club: dict[str, int],
) -> bytes:
    buf = io.StringIO()
    writer = csv.writer(buf)

    writer.writerow(
        [
            "club",
            "income",
        ]
    )

    rows = sorted(
        incomes_by_club.items(),
        key=lambda item: (
            item[0] == NO_CLUB_NAME,
            -item[1],
            item[0].casefold(),
        ),
    )

    for club_name, income in rows:
        writer.writerow(
            [
                club_name,
                income,
            ]
        )

    return buf.getvalue().encode(
        "utf-8"
    )


def get_official_comp_income_csv(
    session: requests.Session,
    comp_id: int,
    progress_callback=None,
) -> tuple[bytes, str]:
    html = (
        fetch_competition_details_html(
            session,
            comp_id,
        )
    )

    validate_official_individual_competition(
        html
    )

    comp_name = extract_competition_name(
        html
    )

    incomes_by_club = (
        collect_competition_incomes_by_club(
            session,
            html,
            progress_callback=(
                progress_callback
            ),
        )
    )

    csv_data = build_income_csv(
        incomes_by_club
    )

    return csv_data, comp_name
