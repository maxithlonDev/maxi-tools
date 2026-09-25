import csv
from pathlib import Path

path = Path("data/world_records_by_nation_season_20_plus.csv")

with path.open("r", encoding="utf-8-sig", newline="") as f:
    rows = list(csv.DictReader(f))

rows.sort(
    key=lambda row: (
        -int(row["WRs"]),
        row["Nation"].casefold(),
    )
)

previous_count = None
rank = 0

for index, row in enumerate(rows, start=1):
    count = int(row["WRs"])

    if count != previous_count:
        rank = index

    row["Rank"] = str(rank)
    previous_count = count

with path.open("w", encoding="utf-8", newline="") as f:
    writer = csv.DictWriter(
        f,
        fieldnames=["Rank", "Nation", "WRs"],
    )
    writer.writeheader()
    writer.writerows(rows)

print(f"Sorted and re-ranked {len(rows)} rows.")
