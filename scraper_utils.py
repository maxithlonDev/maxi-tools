import csv
import io
from bs4 import BeautifulSoup
from urllib.parse import urlparse, parse_qs
import urls as url_utils


def extract_logged_in_user_data(html: str) -> tuple[str, int]:
    soup = BeautifulSoup(html, "html.parser")

    left = soup.find("div", id="left_section")
    if not left:
        raise ValueError("Could not locate user section")

    user_link = left.find(
        "a",
        href=lambda x: x and "dettagli_utente.php" in x
    )
    if not user_link:
        raise ValueError("Could not locate user link")

    username = user_link.get_text(strip=True)

    href = user_link["href"]
    parsed = urlparse(href)
    params = parse_qs(parsed.query)

    if "u" not in params:
        raise ValueError("User id not found in link")

    user_id = int(params["u"][0])

    return username, user_id


def export_athlete_csv(session) -> bytes:
    resp = session.get(url_utils.ATHLETES_URL)
    resp.raise_for_status()

    soup = BeautifulSoup(resp.text, "html.parser")
    _, user_id = extract_logged_in_user_data(resp.text)

    details_resp = session.get(url_utils.get_athlete_details_url(user_id))
    details_resp.raise_for_status()
    details_soup = BeautifulSoup(details_resp.text, "html.parser")

    extra_by_name = {}
    for table in details_soup.find_all("table", id=lambda x: x and x.startswith("atleti")):
        for tr in table.find_all("tr"):
            tds = tr.find_all("td")
            if len(tds) < 8:
                continue
            name = tds[1].get_text(strip=True)
            wage = "".join(c for c in tds[4].get_text() if c.isdigit())
            height = tds[5].get_text(strip=True)
            weight = tds[6].get_text(strip=True)
            exp = tds[7].get_text(strip=True)
            extra_by_name[name] = [height, weight, exp, wage]

    rows = []
    for table in soup.find_all("table", id=lambda x: x and x.startswith("atleti")):
        for tr in table.find_all("tr"):
            tds = tr.find_all("td")
            if len(tds) < 16:
                continue
            name = tds[1].get_text(strip=True)
            stats = [td.get_text(strip=True) for td in tds[3:16]]
            height, weight, exp, wage = extra_by_name.get(name, ["", "", "", ""])
            rows.append([name] + stats + [height, weight, exp, wage])

    buf = io.StringIO()
    writer = csv.writer(buf)
    writer.writerow([
        "Name", "Age", "MAXID", "fans", "care", "form",
        "str", "sta", "spe", "agi", "jmp", "thr", "sp1", "sp2",
        "height", "weight", "exp", "wage"
    ])
    writer.writerows(rows)

    return buf.getvalue().encode("utf-8")
