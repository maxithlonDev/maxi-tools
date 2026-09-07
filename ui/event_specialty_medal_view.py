import streamlit as st

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


def render_specialty_selection(
    sex: str,
) -> list[dict]:
    specialty = st.selectbox(
        "Specialty",
        options=get_specialty_options(),
        format_func=lambda value: (
            SPECIALTY_LABELS[value]
        ),
        key="event_medals_specialty",
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
        events = grouped_events[
            specialty
        ]

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

            disabled = (
                not is_selected
                and prospective_count
                > MAX_SELECTED_EVENT_RESULTS
            )

            with columns[index % 2]:
                selected = st.checkbox(
                    event.label,
                    key=checkbox_key,
                    disabled=disabled,
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


@st.fragment
def render_event_specialty_medal_tool():
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

    countries = history["countries"]

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
        )

    with to_column:
        to_season = st.selectbox(
            "To season",
            options=available_seasons,
            index=0,
            key="event_medals_to_season",
        )

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
                sex
            )
        )
    else:
        expanded_events = (
            render_specialty_selection(
                sex
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

    st.caption(
        (
            f"{estimate['event_pages']} event results"
            f" · "
            f"ETA ~{format_eta(estimate['eta_seconds'])}"
        )
    )

    can_run = (
        inc_count > 0
        and bool(expanded_events)
        and len(expanded_events)
        <= MAX_SELECTED_EVENT_RESULTS
    )

    if st.button(
        "Run aggregation",
        disabled=not can_run,
        use_container_width=True,
        key="event_medals_run",
    ):
        st.info(
            "Crawler backend will be added next."
        )
