import csv
import io
from bs4 import BeautifulSoup
from urls import ATHLETES_URL


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
