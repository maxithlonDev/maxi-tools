from pathlib import Path

import streamlit as st
import streamlit.components.v1 as components


_COMPONENT_PATH = (
    Path(__file__).parent
    / "compact_switch_component"
)

_compact_switch = components.declare_component(
    "compact_switch",
    path=str(_COMPONENT_PATH),
)


def inject_compact_switch_css():
    pass


def render_compact_switch(
    *,
    heading: str,
    left_text: str,
    right_text: str,
    options: tuple[str, ...],
    default_index: int,
    state_key: str,
    container_key: str,
    column_widths: list[float],
) -> str:
    del column_widths

    if len(options) not in (2, 3):
        raise ValueError(
            "Compact switch supports only 2 or 3 positions."
        )

    if (
        state_key not in st.session_state
        or st.session_state[state_key]
        not in options
    ):
        st.session_state[state_key] = (
            options[default_index]
        )

    current_value = (
        st.session_state[state_key]
    )

    value = _compact_switch(
        heading=heading,
        left_text=left_text,
        right_text=right_text,
        options=list(options),
        value=current_value,
        key=container_key,
        default=current_value,
    )

    if value in options:
        st.session_state[state_key] = value

    return st.session_state[state_key]
