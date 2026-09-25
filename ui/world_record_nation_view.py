import csv
from pathlib import Path

import streamlit as st


ROOT_DIR = Path(__file__).resolve().parent.parent

CSV_PATHS = (
    ROOT_DIR
    / "data"
    / "world_records_by_nation_season_20_plus.csv",
    ROOT_DIR
    / "Data"
    / "world_records_by_nation_season_20_plus.csv",
)


def find_csv_path() -> Path:
    for path in CSV_PATHS:
        if path.is_file():
            return path

    raise FileNotFoundError(
        (
            "Could not find "
            "world_records_by_nation_season_20_plus.csv "
            "in data/ or Data/."
        )
    )


def load_rows() -> list[dict]:
    path = find_csv_path()

    with path.open(
        "r",
        encoding="utf-8-sig",
        newline="",
    ) as file:
        reader = csv.DictReader(
            file
        )

        rows = []

        for row in reader:
            try:
                rank = int(
                    row["Rank"]
                )
                records = int(
                    row["WRs"]
                )
            except (
                KeyError,
                TypeError,
                ValueError,
            ):
                continue

            rows.append(
                {
                    "Rank": rank,
                    "Nation": row.get(
                        "Nation",
                        "",
                    ),
                    "WRs": records,
                }
            )

    return rows


@st.fragment
def render_world_record_nation_tool():
    try:
        rows = load_rows()
    except (
        FileNotFoundError,
        OSError,
    ) as exc:
        st.error(
            str(exc)
        )
        return

    if not rows:
        st.warning(
            "The WR by Nation CSV contains no rows."
        )
        return

    total_records = sum(
        row["WRs"]
        for row in rows
    )

    st.caption(
        (
            f"{total_records} world-record "
            "performances since season 20"
            f" · "
            f"{len(rows)} nations"
        )
    )

    st.dataframe(
        rows,
        hide_index=True,
        use_container_width=True,
        height=900,
        column_config={
            "Rank": (
                st.column_config
                .NumberColumn(
                    "Rank",
                    format="%d",
                    width="small",
                )
            ),
            "Nation": (
                st.column_config
                .TextColumn(
                    "Nation",
                    width="large",
                )
            ),
            "WRs": (
                st.column_config
                .NumberColumn(
                    "WRs",
                    format="%d",
                    width="small",
                )
            ),
        },
    )
