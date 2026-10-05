from __future__ import annotations

from html import escape
from pathlib import Path
import base64
import mimetypes

from models import (
    FamilyTreeData,
    Person
)

from connections import (
    orthogonal_path,
    spouse_path,
    CONNECTION_WIDTH
)


BOX_W = 220
BOX_H = 110
MAX_BOX_W = BOX_W * 1.5


def box_width(
    data: FamilyTreeData,
    person: Person
) -> float:

    longest = max(
        len(person.first_name or ""),
        len(person.family_name or ""),
        1
    )

    required = (
        longest * 9
        + 30
    )

    return min(
        MAX_BOX_W,
        max(
            BOX_W,
            required
        )
    )


def font_size(
    data,
    person
):

    width = box_width(
        data,
        person
    )

    longest = max(
        len(person.first_name or ""),
        len(person.family_name or ""),
        1
    )

    available = width - 20

    estimated = (
        longest
        * 16
        * 0.58
    )

    if estimated <= available:
        return 16

    return max(
        8,
        int(
            16
            * available
            / estimated
        )
    )


def person_background(
    data,
    person
):

    width = box_width(
        data,
        person
    )

    colors = data.get_family_colors(
        person.family_name
    )

    if len(colors) == 1:

        return (
            f'<rect '
            f'x="{person.x}" '
            f'y="{person.y}" '
            f'width="{width}" '
            f'height="{BOX_H}" '
            f'fill="{escape(colors[0])}" '
            f'rx="8"/>'
        )

    stripe_width = (
        width / len(colors)
    )

    output = []

    for index, color in enumerate(
        colors
    ):

        output.append(
            f'<rect '
            f'x="{person.x + index * stripe_width:.2f}" '
            f'y="{person.y}" '
            f'width="{stripe_width + 0.5:.2f}" '
            f'height="{BOX_H}" '
            f'fill="{escape(color)}"/>'
        )

    output.append(
        f'<rect '
        f'x="{person.x}" '
        f'y="{person.y}" '
        f'width="{width}" '
        f'height="{BOX_H}" '
        f'fill="none" '
        f'stroke="#222222" '
        f'stroke-width="2" '
        f'rx="8"/>'
    )

    return "".join(
        output
    )


def background_svg(
    data
):

    source = data.background.source

    if not source:
        return ""

    # HTTP(S) kann der SVG-Viewer selbst laden.
    if (
        source.startswith("http://")
        or
        source.startswith("https://")
    ):

        if data.background.mode == "stretch":

            return (
                f'<image '
                f'href="{escape(source)}" '
                f'x="0" y="0" '
                f'width="100%" '
                f'height="100%" '
                f'preserveAspectRatio="none"/>'
            )

        # Tile bei externen URLs:
        # SVG pattern mit image.
        return (
            '<defs>'
            '<pattern '
            'id="backgroundPattern" '
            'patternUnits="userSpaceOnUse" '
            'width="500" '
            'height="500">'
            f'<image '
            f'href="{escape(source)}" '
            'x="0" y="0" '
            'width="500" '
            'height="500" '
            'preserveAspectRatio="xMidYMid slice"/>'
            '</pattern>'
            '</defs>'
            '<rect '
            'x="0" y="0" '
            'width="100%" '
            'height="100%" '
            'fill="url(#backgroundPattern)"/>'
        )

    # Lokale Datei als Data URI einbetten.
    path = Path(source)

    if not path.is_file():
        return ""

    try:

        mime = (
            mimetypes.guess_type(
                str(path)
            )[0]
            or "image/png"
        )

        encoded = base64.b64encode(
            path.read_bytes()
        ).decode(
            "ascii"
        )

        uri = (
            f"data:{mime};base64,"
            f"{encoded}"
        )

        if data.background.mode == "stretch":

            return (
                f'<image '
                f'href="{uri}" '
                f'x="0" y="0" '
                f'width="100%" '
                f'height="100%" '
                f'preserveAspectRatio="none"/>'
            )

        return (
            '<defs>'
            '<pattern '
            'id="backgroundPattern" '
            'patternUnits="userSpaceOnUse" '
            'width="500" '
            'height="500">'
            f'<image '
            f'href="{uri}" '
            'x="0" y="0" '
            'width="500" '
            'height="500" '
            'preserveAspectRatio="xMidYMid slice"/>'
            '</pattern>'
            '</defs>'
            '<rect '
            'x="0" y="0" '
            'width="100%" '
            'height="100%" '
            'fill="url(#backgroundPattern)"/>'
        )

    except OSError:
        return ""


def export_svg(
    data: FamilyTreeData,
    path: str
):

    if not data.persons:

        width = 1200
        height = 800

    else:

        width = max(
            1200,
            max(
                p.x
                + box_width(data, p)
                for p in data.persons.values()
            ) + 100
        )

        height = max(
            800,
            max(
                p.y + BOX_H
                for p in data.persons.values()
            ) + 100
        )

    parts = [
        (
            '<svg '
            'xmlns="http://www.w3.org/2000/svg" '
            f'width="{width}" '
            f'height="{height}" '
            f'viewBox="0 0 {width} {height}">'
        ),

        background_svg(
            data
        ),

        '<g id="connections" '
        'fill="none" '
        'stroke="#333333" '
        f'stroke-width="{CONNECTION_WIDTH}">'
    ]

    # -------------------------------------------------------------
    # Verbindungen
    # -------------------------------------------------------------

    for connection in data.connections:

        a = data.persons.get(
            connection.source
        )

        b = data.persons.get(
            connection.target
        )

        if not a or not b:
            continue

        if connection.relation == "spouse":

            path_data = spouse_path(
                a,
                b,
                box_width(data, a),
                BOX_H
            )

        else:

            path_data = orthogonal_path(
                a,
                b,
                box_width(data, a),
                BOX_H
            )

        dash = (
            ' stroke-dasharray="10 7"'
            if connection.dashed
            else ""
        )

        parts.append(
            f'<path '
            f'd="{path_data}"'
            f'{dash}/>'
        )

    parts.append(
        "</g>"
    )

    # -------------------------------------------------------------
    # Personen
    # -------------------------------------------------------------

    parts.append(
        '<g id="persons" '
        'font-family="Arial, sans-serif">'
    )

    for person in data.persons.values():

        width = box_width(
            data,
            person
        )

        size = font_size(
            data,
            person
        )

        parts.append(
            person_background(
                data,
                person
            )
        )

        # Vorname
        parts.append(
            f'<text '
            f'x="{person.x + 10}" '
            f'y="{person.y + 27}" '
            f'font-size="{size}" '
            f'font-weight="bold">'
            f'{escape(person.first_name)}'
            f'</text>'
        )

        # Familienname
        parts.append(
            f'<text '
            f'x="{person.x + 10}" '
            f'y="{person.y + 49}" '
            f'font-size="{size}">'
            f'{escape(person.family_name)}'
            f'</text>'
        )

        # Geburt
        parts.append(
            f'<text '
            f'x="{person.x + 10}" '
            f'y="{person.y + 74}" '
            f'font-size="11">'
            f'Geb.: '
            f'{escape(person.birth_date or "—")}'
            f'</text>'
        )

        # Tod
        parts.append(
            f'<text '
            f'x="{person.x + 10}" '
            f'y="{person.y + 94}" '
            f'font-size="11">'
            f'Tod: '
            f'{escape(person.death_date or "—")}'
            f'</text>'
        )

        # Welt-Link
        if person.link:

            parts.append(
                f'<a href="{escape(person.link)}">'
                f'<text '
                f'x="{person.x + width - 24}" '
                f'y="{person.y + 21}" '
                f'font-size="17">'
                f'🌐'
                f'</text>'
                f'</a>'
            )

    parts.append(
        "</g></svg>"
    )

    Path(path).write_text(
        "\n".join(parts),
        encoding="utf-8"
    )