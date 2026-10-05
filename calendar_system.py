from datetime import date


MONTHS = [
    "Praios",
    "Rondra",
    "Efferd",
    "Travia",
    "Boron",
    "Hesinde",
    "Firun",
    "Tsa",
    "Phex",
    "Peraine",
    "Ingerimm",
    "Rahja",
]


def gregorian_to_dsa(d: date) -> str:
    """
    Platzhalter für die spätere exakte DSA-Kalenderlogik.
    """
    return d.isoformat()


def format_dsa_day(
    day: int,
    month: str,
    year: int,
    era: str = "BF"
) -> str:
    return f"{day}. {month} {year} {era}"