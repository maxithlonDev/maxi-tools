import csv
import io
from bs4 import BeautifulSoup
from urls import ATHLETES_URL


def extract_logged_in_username(html: str) -> str:
    soup = BeautifulSoup(html, "html.parser")

    left = soup.find("div", id="left_section")
    if not left:
        raise ValueError("Could not locate user section")

    user_link = left.find(
        "a",
        href=lambda x: x and "dettagli_utente.php" in x
    )
    if not user_link:
        raise ValueError("Could not extract username")

    return user_link.get_text(strip=True)


def export_athlete_csv(session) -> bytes:
    resp = session.get(ATHLETES_URL)
    resp.raise_for_status()

    soup = BeautifulSoup(resp.text, "html.parser")

    tables = soup.find_all("table", id=lambda x: x and x.startswith("atleti"))

    rows = []
    for table in tables:
        for tr in table.find_all("tr"):
            tds = tr.find_all("td")
            if len(tds) < 16:
                continue

            name = tds[1].get_text(strip=True)
            stats = [td.get_text(strip=True) for td in tds[3:16]]
            rows.append([name] + stats)

    buf = io.StringIO()
    writer = csv.writer(buf)
    writer.writerow([
        "Name", "Age", "MAXID", "fans", "care", "form",
        "str", "sta", "spe", "agi", "jmp", "thr", "sp1", "sp2"
    ])
    writer.writerows(rows)

    return buf.getvalue().encode("utf-8")
