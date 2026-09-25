from dataclasses import dataclass


SEX_MEN = "Men"
SEX_WOMEN = "Women"
SEX_BOTH = "Both"

SELECTION_SPECIALTY = "Specialty"
SELECTION_EVENTS = "Events"

MAX_SELECTED_EVENT_RESULTS = 10


@dataclass(frozen=True)
class EventDefinition:
    key: str
    label: str
    specialty: str
    men_name: str | None = None
    women_name: str | None = None

    def supports_sex(
        self,
        sex: str,
    ) -> bool:
        if sex == SEX_MEN:
            return self.men_name is not None

        if sex == SEX_WOMEN:
            return self.women_name is not None

        if sex == SEX_BOTH:
            return (
                self.men_name is not None
                or self.women_name is not None
            )

        return False

    def result_count(
        self,
        sex: str,
    ) -> int:
        count = 0

        if (
            sex in (SEX_MEN, SEX_BOTH)
            and self.men_name is not None
        ):
            count += 1

        if (
            sex in (SEX_WOMEN, SEX_BOTH)
            and self.women_name is not None
        ):
            count += 1

        return count


SPECIALTIES = (
    "SPR",
    "MDR",
    "LDR",
    "RW",
    "JMP",
    "THR",
    "Combined",
    "Relay",
)


EVENTS = (
    EventDefinition(
        key="100m",
        label="100 Meters",
        specialty="SPR",
        men_name="100 Meters",
        women_name="100 Meters",
    ),
    EventDefinition(
        key="200m",
        label="200 Meters",
        specialty="SPR",
        men_name="200 Meters",
        women_name="200 Meters",
    ),
    EventDefinition(
        key="400m",
        label="400 Meters",
        specialty="SPR",
        men_name="400 Meters",
        women_name="400 Meters",
    ),
    EventDefinition(
        key="short_hurdles",
        label="100/110 hurdles",
        specialty="SPR",
        men_name="110 hurdles",
        women_name="100 hurdles",
    ),
    EventDefinition(
        key="400h",
        label="400 hurdles",
        specialty="SPR",
        men_name="400 hurdles",
        women_name="400 hurdles",
    ),
    EventDefinition(
        key="800m",
        label="800 Meters",
        specialty="MDR",
        men_name="800 Meters",
        women_name="800 Meters",
    ),
    EventDefinition(
        key="1500m",
        label="1500 Meters",
        specialty="MDR",
        men_name="1500 Meters",
        women_name="1500 Meters",
    ),
    EventDefinition(
        key="3000sc",
        label="3000 m steeplechase",
        specialty="MDR",
        men_name="3000 m steeplechase",
        women_name="3000 m steeplechase",
    ),
    EventDefinition(
        key="5000m",
        label="5000 Meters",
        specialty="LDR",
        men_name="5000 Meters",
        women_name="5000 Meters",
    ),
    EventDefinition(
        key="10000m",
        label="10000 Meters",
        specialty="LDR",
        men_name="10000 Meters",
        women_name="10000 Meters",
    ),
    EventDefinition(
        key="marathon",
        label="Marathon",
        specialty="LDR",
        men_name="Marathon",
        women_name="Marathon",
    ),
    EventDefinition(
        key="10rw",
        label="10Km Race Walk",
        specialty="RW",
        men_name="10Km Race Walk",
        women_name="10Km Race Walk",
    ),
    EventDefinition(
        key="20rw",
        label="20Km Race Walk",
        specialty="RW",
        men_name="20Km Race Walk",
        women_name="20Km Race Walk",
    ),
    EventDefinition(
        key="50rw",
        label="50Km Race Walk",
        specialty="RW",
        men_name="50Km Race Walk",
        women_name="50Km Race Walk",
    ),
    EventDefinition(
        key="hj",
        label="High jump",
        specialty="JMP",
        men_name="High jump",
        women_name="High jump",
    ),
    EventDefinition(
        key="pv",
        label="Pole vault",
        specialty="JMP",
        men_name="Pole vault",
        women_name="Pole vault",
    ),
    EventDefinition(
        key="lj",
        label="Long jump",
        specialty="JMP",
        men_name="Long jump",
        women_name="Long jump",
    ),
    EventDefinition(
        key="tj",
        label="Triple jump",
        specialty="JMP",
        men_name="Triple jump",
        women_name="Triple jump",
    ),
    EventDefinition(
        key="sp",
        label="Shot put",
        specialty="THR",
        men_name="Shot put",
        women_name="Shot put",
    ),
    EventDefinition(
        key="dt",
        label="Discus",
        specialty="THR",
        men_name="Discus",
        women_name="Discus",
    ),
    EventDefinition(
        key="ht",
        label="Hammer",
        specialty="THR",
        men_name="Hammer",
        women_name="Hammer",
    ),
    EventDefinition(
        key="jt",
        label="Javelin",
        specialty="THR",
        men_name="Javelin",
        women_name="Javelin",
    ),
    EventDefinition(
        key="pentathlon",
        label="Pentathlon",
        specialty="Combined",
        men_name="Pentathlon Men",
        women_name="Pentathlon Women",
    ),
    EventDefinition(
        key="long_combined",
        label="Decathlon / Heptathlon",
        specialty="Combined",
        men_name="Decathlon",
        women_name="Heptathlon",
    ),
    EventDefinition(
        key="relay4x100",
        label="Relay 4x100",
        specialty="Relay",
        men_name="Relay 4x100",
        women_name="Relay 4x100",
    ),
    EventDefinition(
        key="relay4x400",
        label="Relay 4x400",
        specialty="Relay",
        men_name="Relay 4x400",
        women_name="Relay 4x400",
    ),
)


EVENT_BY_KEY = {
    event.key: event
    for event in EVENTS
}


def get_specialty_options() -> tuple[str, ...]:
    return SPECIALTIES


def get_events_for_specialty(
    specialty: str,
    sex: str,
) -> list[EventDefinition]:
    return [
        event
        for event in EVENTS
        if (
            event.specialty == specialty
            and event.supports_sex(sex)
        )
    ]


def get_grouped_event_options(
    sex: str,
) -> dict[str, list[EventDefinition]]:
    return {
        specialty: get_events_for_specialty(
            specialty,
            sex,
        )
        for specialty in SPECIALTIES
    }


def count_selected_event_results(
    event_keys: list[str],
    sex: str,
) -> int:
    return sum(
        EVENT_BY_KEY[event_key].result_count(
            sex
        )
        for event_key in event_keys
        if event_key in EVENT_BY_KEY
    )


def validate_event_selection(
    event_keys: list[str],
    sex: str,
):
    total = count_selected_event_results(
        event_keys,
        sex,
    )

    if total > MAX_SELECTED_EVENT_RESULTS:
        raise ValueError(
            (
                "Select at most "
                f"{MAX_SELECTED_EVENT_RESULTS} "
                "total men's/women's event results."
            )
        )


def expand_event_selection(
    event_keys: list[str],
    sex: str,
) -> list[dict]:
    validate_event_selection(
        event_keys,
        sex,
    )

    expanded = []

    for event_key in event_keys:
        event = EVENT_BY_KEY.get(
            event_key
        )

        if event is None:
            continue

        if (
            sex in (SEX_MEN, SEX_BOTH)
            and event.men_name is not None
        ):
            expanded.append(
                {
                    "sex": SEX_MEN,
                    "event_key": event.key,
                    "event_name": event.men_name,
                    "specialty": event.specialty,
                }
            )

        if (
            sex in (SEX_WOMEN, SEX_BOTH)
            and event.women_name is not None
        ):
            expanded.append(
                {
                    "sex": SEX_WOMEN,
                    "event_key": event.key,
                    "event_name": event.women_name,
                    "specialty": event.specialty,
                }
            )

    return expanded


def expand_specialty_selection(
    specialty: str,
    sex: str,
) -> list[dict]:
    event_keys = [
        event.key
        for event in get_events_for_specialty(
            specialty,
            sex,
        )
    ]

    return expand_event_selection(
        event_keys,
        sex,
    )
