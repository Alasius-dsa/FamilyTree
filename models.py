from __future__ import annotations

from dataclasses import dataclass, field
from typing import Optional
import json
from pathlib import Path


@dataclass
class Person:
    id: str
    first_name: str = ""
    family_name: str = ""
    birth_date: str = ""
    death_date: str = ""
    link: str = ""

    # Position im Stammbaum
    x: float = 100.0
    y: float = 100.0

    def display_name(self) -> str:
        return " ".join(
            p for p in (self.first_name, self.family_name)
            if p
        ).strip() or "(Unbenannt)"


@dataclass
class Family:
    name: str
    color: str = "#ffffff"


@dataclass
class Connection:
    source: str
    target: str
    relation: str
    dashed: bool = False


@dataclass
class BackgroundSettings:
    source: str = ""
    mode: str = "tile"

    # "tile" oder "stretch"


@dataclass
class FamilyTreeData:
    persons: dict[str, Person] = field(default_factory=dict)
    connections: list[Connection] = field(default_factory=list)

    # Familienname -> Family
    families: dict[str, Family] = field(default_factory=dict)

    background: BackgroundSettings = field(
        default_factory=BackgroundSettings
    )

    # =============================================================
    # Personen
    # =============================================================

    def add_person(self, person: Person) -> None:
        self.persons[person.id] = person

        self.ensure_families_for_person(person)

    def remove_person(self, person_id: str) -> None:
        self.persons.pop(
            person_id,
            None
        )

        self.connections = [
            c
            for c in self.connections
            if c.source != person_id
            and c.target != person_id
        ]

    # =============================================================
    # Familien
    # =============================================================

    def ensure_family(
        self,
        family_name: str
    ) -> Family | None:

        family_name = family_name.strip()

        if not family_name:
            return None

        if family_name not in self.families:
            self.families[family_name] = Family(
                name=family_name
            )

        return self.families[family_name]

    def ensure_families_for_person(
        self,
        person: Person
    ) -> None:

        for family_name in self.extract_family_names(
            person.family_name
        ):
            self.ensure_family(
                family_name
            )

    def extract_family_names(
        self,
        family_name: str
    ) -> list[str]:

        """
        Erlaubt mehrere Häuser in einem Familiennamen.

        Beispiele:

            "B"
                -> ["B"]

            "B-C"
                -> ["B", "C"]

            "von B-C"
                -> ["von B", "C"]

        Für komplexere Namenssysteme können wir diese
        Funktion später erweitern.
        """

        family_name = family_name.strip()

        if not family_name:
            return []

        # Bindestrich als Trennung gemischter Häuser.
        #
        # Wir entfernen nur Leerzeichen um den Bindestrich,
        # damit "B-C" und "B - C" identisch behandelt werden.

        if "-" in family_name:
            parts = [
                part.strip()
                for part in family_name.split("-")
                if part.strip()
            ]

            return parts

        return [family_name]

    def get_family_colors(
        self,
        family_name: str
    ) -> list[str]:

        colors = []

        for name in self.extract_family_names(
            family_name
        ):
            family = self.families.get(name)

            if family:
                colors.append(
                    family.color
                )

        if not colors:
            colors.append("#ffffff")

        return colors

    def rename_family(
        self,
        old_name: str,
        new_name: str
    ) -> None:

        old_name = old_name.strip()
        new_name = new_name.strip()

        if not old_name or not new_name:
            return

        if old_name not in self.families:
            return

        if old_name == new_name:
            return

        family = self.families.pop(
            old_name
        )

        family.name = new_name

        self.families[new_name] = family

        # Personen entsprechend aktualisieren.
        for person in self.persons.values():

            names = self.extract_family_names(
                person.family_name
            )

            if old_name not in names:
                continue

            names = [
                new_name if n == old_name else n
                for n in names
            ]

            person.family_name = "-".join(
                names
            )

    def remove_family(
        self,
        family_name: str
    ) -> None:

        self.families.pop(
            family_name,
            None
        )

    # =============================================================
    # Verbindungen
    # =============================================================

    def connect(
        self,
        source: str,
        target: str,
        relation: str
    ) -> None:

        if source == target:
            return

        dashed = relation == "spouse"

        if any(
            c.source == source
            and c.target == target
            and c.relation == relation
            for c in self.connections
        ):
            return

        self.connections.append(
            Connection(
                source=source,
                target=target,
                relation=relation,
                dashed=dashed
            )
        )

    def disconnect(
        self,
        source: str,
        target: str,
        relation: Optional[str] = None
    ) -> None:

        self.connections = [
            c
            for c in self.connections
            if not (
                c.source == source
                and c.target == target
                and (
                    relation is None
                    or c.relation == relation
                )
            )
        ]

    def get_connections_for(
        self,
        person_id: str
    ) -> list[Connection]:

        return [
            c
            for c in self.connections
            if c.source == person_id
            or c.target == person_id
        ]

    # =============================================================
    # Speichern
    # =============================================================

    def save(
        self,
        path: str
    ) -> None:

        payload = {
            "persons": {
                k: vars(v)
                for k, v in self.persons.items()
            },

            "connections": [
                vars(c)
                for c in self.connections
            ],

            "families": {
                k: vars(v)
                for k, v in self.families.items()
            },

            "background": vars(
                self.background
            )
        }

        Path(path).write_text(
            json.dumps(
                payload,
                ensure_ascii=False,
                indent=2
            ),
            encoding="utf-8"
        )

    # =============================================================
    # Laden
    # =============================================================

    @classmethod
    def load(
        cls,
        path: str
    ) -> "FamilyTreeData":

        raw = json.loads(
            Path(path).read_text(
                encoding="utf-8"
            )
        )

        data = cls()

        # ---------------------------------------------------------
        # Personen
        # ---------------------------------------------------------

        for pid, p in raw.get(
            "persons",
            {}
        ).items():

            # Alte Version enthielt house_colors.
            # Diese werden ignoriert.

            person_data = {
                k: v
                for k, v in p.items()
                if k not in (
                    "id",
                    "house_colors"
                )
            }

            person = Person(
                id=pid,
                **person_data
            )

            data.persons[pid] = person

        # ---------------------------------------------------------
        # Familien
        # ---------------------------------------------------------

        for name, family_data in raw.get(
            "families",
            {}
        ).items():

            data.families[name] = Family(
                name=name,
                color=family_data.get(
                    "color",
                    "#ffffff"
                )
            )

        # Falls eine alte Datei noch keine
        # Familienliste besitzt:
        for person in data.persons.values():
            data.ensure_families_for_person(
                person
            )

        # ---------------------------------------------------------
        # Verbindungen
        # ---------------------------------------------------------

        for c in raw.get(
            "connections",
            []
        ):

            data.connections.append(
                Connection(
                    **c
                )
            )

        # ---------------------------------------------------------
        # Hintergrund
        # ---------------------------------------------------------

        background = raw.get(
            "background",
            {}
        )

        data.background = BackgroundSettings(
            source=background.get(
                "source",
                ""
            ),
            mode=background.get(
                "mode",
                "tile"
            )
        )

        return data