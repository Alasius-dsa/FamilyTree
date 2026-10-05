from __future__ import annotations

from models import (
    FamilyTreeData,
    Person
)


CONNECTION_WIDTH = 4


def add_parent_child(
    data: FamilyTreeData,
    parent_id: str,
    child_id: str
) -> None:

    data.connect(
        parent_id,
        child_id,
        "parent"
    )


def add_spouse(
    data: FamilyTreeData,
    person_a: str,
    person_b: str
) -> None:

    data.connect(
        person_a,
        person_b,
        "spouse"
    )


def connection_description(
    data: FamilyTreeData,
    connection,
    person_id: str
) -> tuple[str, str]:

    """
    Liefert:

        (Bezeichnung, andere_person_id)

    aus Sicht der angegebenen Person.
    """

    if connection.relation == "spouse":

        other = (
            connection.target
            if connection.source == person_id
            else connection.source
        )

        return (
            "Ehegatte/Ehegattin",
            other
        )

    # Eltern-Kind-Verbindung

    if connection.target == person_id:
        return (
            "Elternteil",
            connection.source
        )

    return (
        "Kind",
        connection.target
    )


def orthogonal_path(
    a: Person,
    b: Person,
    box_width: float,
    box_height: float
) -> str:

    ax = a.x + box_width / 2
    ay = a.y + box_height

    bx = b.x + box_width / 2
    by = b.y

    mid_y = (ay + by) / 2

    return (
        f"M {ax} {ay} "
        f"L {ax} {mid_y} "
        f"L {bx} {mid_y} "
        f"L {bx} {by}"
    )


def spouse_path(
    a: Person,
    b: Person,
    box_width: float,
    box_height: float
) -> str:

    ax = a.x + box_width
    ay = a.y + box_height / 2

    bx = b.x
    by = b.y + box_height / 2

    mid_x = (ax + bx) / 2

    return (
        f"M {ax} {ay} "
        f"L {mid_x} {ay} "
        f"L {mid_x} {by} "
        f"L {bx} {by}"
    )