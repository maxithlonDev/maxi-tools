import time

import streamlit as st

from tools.event_specialty_medal_crawler import (
    crawl_event_medals,
)
from tools.event_specialty_medal_tool import (
    MAX_SELECTED_EVENT_RESULTS,
    SELECTION_EVENTS,
    SELECTION_SPECIALTY,
    SEX_BOTH,
    SEX_MEN,
    SEX_WOMEN,
    count_selected_event_results,
    expand_event_selection,
    expand_specialty_selection,
    get_grouped_event_options,
    get_specialty_options,
)
from tools.inc_history_tool import (
    get_available_seasons,
    get_country_options,
    load_inc_history,
)
from ui.compact_switch import (
    inject_compact_switch_css,
    render_compact_switch,
)
from ui.event_medal_estimate import (
    build_load_estimate,
    count_inc_competitions,
    format_eta,
)


SPECIALTY_LABELS = {
    "SPR": "Sprint",
    "MDR": "Middle Distance",
    "LDR": "Long Distance",
    "RW": "Race Walk",
    "JMP": "Jump",
    "THR": "Throw",
    "Combined": "Combined",
    "Relay": "Relay",
}

DEFAULT_SECONDS_PER_PAGE = 0.3


def initialize_state():
    defaults = {
        "event_medals_running": False,
        "event_medals_job": None,
        "event_medals_result": None,
        "event_medals_error": None,
        "event_medals_total_pages_timed": 0,
        "event_medals_total_timed_seconds": 0.0,
        "event_medals_last_elapsed_seconds": None,
        "event_medals_last_pages_per_second": None,
    }

    for key, value in defaults.items():
        if key not in st.session_state:
            st.session_state[key] = value


def get_estimated_seconds_per_page() -> float:
    total_pages = st.session_state.get(
        "event_medals_total_pages_timed",
        0,
    )

    total_seconds = st.session_state.get(
        "event_medals_total_timed_seconds",
        0.0,
    )

    if (
        total_pages > 0
        and total_seconds > 0
    ):
        return (
            total_seconds
            / total_pages
        )

    return DEFAULT_SECONDS_PER_PAGE


def render_selector_row() -> tuple[str, str]:
    inject_compact_switch_css()

    sex_column, selection_column = st.columns(
        2,
        gap="large",
    )

    with sex_column:
        sex = render_compact_switch(
            heading="Sex",
            left_text="M",
            right_text="W",
            options=(
                SEX_MEN,
                SEX_BOTH,
                SEX_WOMEN,
            ),
            default_index=1,
            state_key="event_medals_sex",
            container_key="compact_sex_switch",
            column_widths=[],
        )

    with selection_column:
        selection_type = (
            render_compact_switch(
                heading="Selection Type",
                left_text="Spec",
                right_text="Event",
                options=(
                    SELECTION_SPECIALTY,
                    SELECTION_EVENTS,
                ),
                default_index=0,
                state_key=(
                    "event_medals_selection_type"
                ),
                container_key=(
                    "compact_selection_switch"
                ),
                column_widths=[],
            )
        )

    return (
        sex,
        selection_type,
    )


def render_locked_selector_row(
    job: dict,
):
    sex_column, selection_column = st.columns(
        2,
        gap="large",
    )

    with sex_column:
        st.markdown("**Sex**")
        st.caption(job["sex"])

    with selection_column:
        st.markdown(
            "**Selection Type**"
        )
        st.caption(
            job["selection_type"]
        )


def render_specialty_selection(
    sex: str,
    disabled: bool,
) -> list[dict]:
    specialty = st.selectbox(
        "Specialty",
        options=get_specialty_options(),
        format_func=lambda value: (
            SPECIALTY_LABELS[value]
        ),
        key="event_medals_specialty",
        disabled=disabled,
    )

    return expand_specialty_selection(
        specialty,
        sex,
    )


def get_selected_event_keys(
    grouped_events,
) -> list[str]:
    return [
        event.key
        for events in grouped_events.values()
        for event in events
        if st.session_state.get(
            f"event_medals_event_{event.key}",
            False,
        )
    ]


def render_event_selection(
    sex: str,
    disabled: bool,
) -> list[dict]:
    grouped_events = (
        get_grouped_event_options(
            sex
        )
    )

    selected_keys = (
        get_selected_event_keys(
            grouped_events
        )
    )

    for specialty in get_specialty_options():
        events = grouped_events[specialty]

        if not events:
            continue

        st.markdown(
            f"**{SPECIALTY_LABELS[specialty]}**"
        )

        columns = st.columns(2)

        for index, event in enumerate(
            events
        ):
            checkbox_key = (
                f"event_medals_event_{event.key}"
            )

            is_selected = (
                event.key
                in selected_keys
            )

            other_selected = [
                event_key
                for event_key in selected_keys
                if event_key != event.key
            ]

            prospective_count = (
                count_selected_event_results(
                    [
                        *other_selected,
                        event.key,
                    ],
                    sex,
                )
            )

            event_disabled = (
                disabled
                or (
                    not is_selected
                    and prospective_count
                    > MAX_SELECTED_EVENT_RESULTS
                )
            )

            with columns[index % 2]:
                selected = st.checkbox(
                    event.label,
                    key=checkbox_key,
                    disabled=event_disabled,
                )

            if (
                selected
                and event.key
                not in selected_keys
            ):
                selected_keys.append(
                    event.key
                )

            if (
                not selected
                and event.key
                in selected_keys
            ):
                selected_keys.remove(
                    event.key
                )

    selected_count = (
        count_selected_event_results(
            selected_keys,
            sex,
        )
    )

    if (
        selected_count
        > MAX_SELECTED_EVENT_RESULTS
    ):
        st.error(
            (
                "Select at most "
                f"{MAX_SELECTED_EVENT_RESULTS} "
                "total men's/women's event "
                "results."
            )
        )

        return []

    return expand_event_selection(
        selected_keys,
        sex,
    )


def format_elapsed(
    seconds: float,
) -> str:
    if seconds < 60:
        return f"{seconds:.1f}s"

    minutes = int(
        seconds // 60
    )

    remaining_seconds = int(
        seconds % 60
    )

    return (
        f"{minutes}m "
        f"{remaining_seconds}s"
    )


def format_progress(
    status: dict,
    elapsed_seconds: float,
) -> str:
    page_current = status[
        "page_current"
    ]
    page_total = status[
        "page_total"
    ]
    inc_current = status[
        "inc_current"
    ]
    inc_total = status[
        "inc_total"
    ]
    event_current = status[
        "event_current"
    ]
    event_total = status[
        "event_total"
    ]

    if (
        elapsed_seconds > 0
        and page_current > 0
    ):
        pages_per_second = (
            page_current
            / elapsed_seconds
        )
    else:
        pages_per_second = 0.0

    remaining_pages = max(
        0,
        page_total - page_current,
    )

    if pages_per_second > 0:
        remaining_seconds = (
            remaining_pages
            / pages_per_second
        )
    else:
        remaining_seconds = (
            remaining_pages
            * get_estimated_seconds_per_page()
        )

    return (
        f"INC {inc_current}/{inc_total}"
        f" · "
        f"Event {event_current}/{event_total}"
        f" · "
        f"{page_current}/{page_total} pages"
        f" · "
        f"{pages_per_second:.2f} pages/s"
        f" · "
        f"Elapsed {format_elapsed(elapsed_seconds)}"
        f" · "
        f"ETA ~{format_eta(remaining_seconds)}"
    )


def build_result_rows(
    clubs: list[dict],
) -> list[dict]:
    rows = []

    for rank, club in enumerate(
        clubs,
        start=1,
    ):
        rows.append(
            {
                "Rank": rank,
                "Club": club["name"],
                "Nation": (
                    club.get(
                        "nation_code"
                    )
                    or ""
                ),
                "Gold": club["gold"],
                "Silver": club["silver"],
                "Bronze": club["bronze"],
                "Total": (
                    club["gold"]
                    + club["silver"]
                    + club["bronze"]
                ),
            }
        )

    return rows


def render_result():
    result = st.session_state.get(
        "event_medals_result"
    )

    if result is None:
        return

    rows = build_result_rows(
        result["clubs"]
    )

    st.dataframe(
        rows,
        hide_index=True,
        use_container_width=True,
    )


def start_job(
    *,
    country_id,
    from_season,
    to_season,
    sex,
    selection_type,
    selected_events,
):
    st.session_state[
        "event_medals_job"
    ] = {
        "country_id": country_id,
        "from_season": from_season,
        "to_season": to_season,
        "sex": sex,
        "selection_type": (
            selection_type
        ),
        "selected_events": (
            selected_events
        ),
    }

    st.session_state[
        "event_medals_result"
    ] = None

    st.session_state[
        "event_medals_error"
    ] = None

    st.session_state[
        "event_medals_running"
    ] = True

    st.rerun()


def store_timing(
    *,
    elapsed_seconds: float,
    page_count: int,
):
    if (
        elapsed_seconds <= 0
        or page_count <= 0
    ):
        return

    st.session_state[
        "event_medals_last_elapsed_seconds"
    ] = elapsed_seconds

    st.session_state[
        "event_medals_last_pages_per_second"
    ] = (
        page_count
        / elapsed_seconds
    )

    st.session_state[
        "event_medals_total_pages_timed"
    ] += page_count

    st.session_state[
        "event_medals_total_timed_seconds"
    ] += elapsed_seconds


def run_pending_job(
    history: dict,
):
    if not st.session_state.get(
        "event_medals_running"
    ):
        return

    job = st.session_state.get(
        "event_medals_job"
    )

    if job is None:
        st.session_state[
            "event_medals_running"
        ] = False
        return

    progress = st.empty()
    crawl_start = time.perf_counter()

    def update_progress(
        status: dict,
    ):
        elapsed_seconds = (
            time.perf_counter()
            - crawl_start
        )

        progress.info(
            format_progress(
                status,
                elapsed_seconds,
            )
        )

    try:
        result = crawl_event_medals(
            session=(
                st.session_state.session
            ),
            history=history,
            country_id=job[
                "country_id"
            ],
            from_season=job[
                "from_season"
            ],
            to_season=job[
                "to_season"
            ],
            selected_events=job[
                "selected_events"
            ],
            progress_callback=(
                update_progress
            ),
        )

        elapsed_seconds = (
            time.perf_counter()
            - crawl_start
        )

        store_timing(
            elapsed_seconds=(
                elapsed_seconds
            ),
            page_count=result[
                "page_count"
            ],
        )

        st.session_state[
            "event_medals_result"
        ] = result

        st.session_state[
            "event_medals_error"
        ] = None

    except Exception as exc:
        st.session_state[
            "event_medals_result"
        ] = None

        st.session_state[
            "event_medals_error"
        ] = str(exc)

    finally:
        st.session_state[
            "event_medals_running"
        ] = False

        st.session_state[
            "event_medals_job"
        ] = None

    st.rerun()


@st.fragment
def render_event_specialty_medal_tool():
    initialize_state()

    if (
        st.session_state.get(
            "session"
        )
        is None
    ):
        st.info(
            (
                "Sign in to use the "
                "Event/Specialty Medal Aggregator."
            )
        )
        return

    try:
        history = load_inc_history()
    except (
        FileNotFoundError,
        ValueError,
    ) as exc:
        st.error(
            str(exc)
        )
        return

    running = st.session_state[
        "event_medals_running"
    ]

    job = st.session_state.get(
        "event_medals_job"
    )

    countries = history[
        "countries"
    ]

    country_ids = (
        get_country_options(
            history
        )
    )

    selected_country = st.selectbox(
        "Nation",
        options=country_ids,
        format_func=lambda value: (
            countries[value]["name"]
        ),
        key="event_medals_country",
        disabled=running,
    )

    available_seasons = (
        get_available_seasons(
            history,
            selected_country,
        )
    )

    if not available_seasons:
        st.warning(
            "No seasons are available."
        )
        return

    from_column, to_column = (
        st.columns(2)
    )

    with from_column:
        from_season = st.selectbox(
            "From season",
            options=available_seasons,
            index=0,
            key="event_medals_from_season",
            disabled=running,
        )

    with to_column:
        to_season = st.selectbox(
            "To season",
            options=available_seasons,
            index=0,
            key="event_medals_to_season",
            disabled=running,
        )

    if (
        running
        and job is not None
    ):
        sex = job["sex"]
        selection_type = job[
            "selection_type"
        ]

        render_locked_selector_row(
            job
        )
    else:
        (
            sex,
            selection_type,
        ) = render_selector_row()

    if (
        selection_type
        == SELECTION_EVENTS
    ):
        expanded_events = (
            render_event_selection(
                sex,
                running,
            )
        )
    else:
        expanded_events = (
            render_specialty_selection(
                sex,
                running,
            )
        )

    inc_count = count_inc_competitions(
        history,
        selected_country,
        from_season,
        to_season,
    )

    estimate = build_load_estimate(
        inc_count=inc_count,
        events_per_inc=len(
            expanded_events
        ),
    )

    estimated_seconds = (
        estimate["total_pages"]
        * get_estimated_seconds_per_page()
    )

    st.caption(
        (
            f"{estimate['event_pages']} event results"
            f" · "
            f"ETA ~{format_eta(estimated_seconds)}"
        )
    )

    can_run = (
        not running
        and inc_count > 0
        and bool(expanded_events)
        and len(expanded_events)
        <= MAX_SELECTED_EVENT_RESULTS
    )

    if st.button(
        (
            "Running aggregation..."
            if running
            else "Run aggregation"
        ),
        disabled=not can_run,
        use_container_width=True,
        key="event_medals_run",
    ):
        start_job(
            country_id=selected_country,
            from_season=from_season,
            to_season=to_season,
            sex=sex,
            selection_type=selection_type,
            selected_events=(
                expanded_events
            ),
        )

    if running:
        run_pending_job(
            history
        )
        return

    error = st.session_state.get(
        "event_medals_error"
    )

    if error:
        st.error(
            error
        )

    render_result()
