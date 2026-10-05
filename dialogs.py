from __future__ import annotations

import tkinter as tk
from tkinter import ttk, colorchooser

from models import (
    FamilyTreeData,
    Person
)

from connections import (
    connection_description,
    add_parent_child,
    add_spouse
)


class PersonDialog(tk.Toplevel):

    def __init__(
        self,
        master,
        data: FamilyTreeData,
        person: Person,
        on_save
    ):

        super().__init__(
            master
        )

        self.title(
            f"Person bearbeiten – "
            f"{person.display_name()}"
        )

        self.geometry(
            "780x760"
        )

        self.transient(
            master
        )

        self.grab_set()

        self.data = data
        self.person = person
        self.on_save = on_save

        self._build_ui()

        self._refresh_connections()

    # =============================================================
    # UI
    # =============================================================

    def _build_ui(self):

        outer = ttk.Frame(
            self,
            padding=14
        )

        outer.pack(
            fill="both",
            expand=True
        )

        # ---------------------------------------------------------
        # Grunddaten
        # ---------------------------------------------------------

        ttk.Label(
            outer,
            text="Person",
            font=(
                "Arial",
                14,
                "bold"
            )
        ).pack(
            anchor="w",
            pady=(0, 12)
        )

        basic = ttk.Frame(
            outer
        )

        basic.pack(
            fill="x"
        )

        self.vars = {}

        fields = [
            (
                "Vorname",
                "first_name"
            ),
            (
                "Familienname",
                "family_name"
            ),
            (
                "Geburtsdatum",
                "birth_date"
            ),
            (
                "Todesdatum",
                "death_date"
            ),
            (
                "Link",
                "link"
            )
        ]

        for row, (
            label,
            key
        ) in enumerate(
            fields
        ):

            ttk.Label(
                basic,
                text=label
            ).grid(
                row=row,
                column=0,
                sticky="w",
                pady=3
            )

            variable = tk.StringVar(
                value=getattr(
                    self.person,
                    key
                )
            )

            self.vars[key] = variable

            ttk.Entry(
                basic,
                textvariable=variable,
                width=55
            ).grid(
                row=row,
                column=1,
                sticky="ew",
                padx=8
            )

        basic.columnconfigure(
            1,
            weight=1
        )

        # ---------------------------------------------------------
        # Beziehungen
        # ---------------------------------------------------------

        ttk.Label(
            outer,
            text="Verbindungen",
            font=(
                "Arial",
                12,
                "bold"
            )
        ).pack(
            anchor="w",
            pady=(20, 6)
        )

        self.connection_frame = ttk.Frame(
            outer
        )

        self.connection_frame.pack(
            fill="both",
            expand=True
        )

        # ---------------------------------------------------------
        # Neue Verbindung
        # ---------------------------------------------------------

        ttk.Label(
            outer,
            text="Neue Verbindung",
            font=(
                "Arial",
                11,
                "bold"
            )
        ).pack(
            anchor="w",
            pady=(15, 5)
        )

        new_frame = ttk.Frame(
            outer
        )

        new_frame.pack(
            fill="x"
        )

        self.new_relation = tk.StringVar(
            value="Kind"
        )

        relation_combo = ttk.Combobox(
            new_frame,
            textvariable=self.new_relation,
            values=[
                "Vater",
                "Mutter",
                "Kind",
                "Ehegatte/Ehegattin"
            ],
            state="readonly",
            width=20
        )

        relation_combo.pack(
            side="left"
        )

        self.new_person = ttk.Combobox(
            new_frame,
            values=self._person_names(),
            width=42
        )

        self.new_person.pack(
            side="left",
            padx=8,
            fill="x",
            expand=True
        )

        ttk.Button(
            new_frame,
            text="Hinzufügen",
            command=self.add_connection
        ).pack(
            side="left"
        )

        # ---------------------------------------------------------
        # Buttons
        # ---------------------------------------------------------

        buttons = ttk.Frame(
            outer
        )

        buttons.pack(
            fill="x",
            pady=(15, 0)
        )

        ttk.Button(
            buttons,
            text="Abbrechen",
            command=self.destroy
        ).pack(
            side="right"
        )

        ttk.Button(
            buttons,
            text="Speichern",
            command=self.save
        ).pack(
            side="right",
            padx=8
        )

    # =============================================================
    # Personen
    # =============================================================

    def _person_names(self):

        return [
            person.display_name()
            for person in self.data.persons.values()
            if person.id != self.person.id
        ]

    def _find_or_create(
        self,
        name
    ) -> Person | None:

        name = name.strip()

        if not name:
            return None

        for person in self.data.persons.values():

            if (
                person.display_name().lower()
                == name.lower()
            ):
                return person

        parts = name.split(
            maxsplit=1
        )

        first_name = parts[0]

        family_name = (
            parts[1]
            if len(parts) > 1
            else ""
        )

        import uuid

        person = Person(
            id=str(uuid.uuid4()),
            first_name=first_name,
            family_name=family_name
        )

        self.data.add_person(
            person
        )

        return person

    # =============================================================
    # Verbindungen anzeigen
    # =============================================================

    def _refresh_connections(self):

        for child in self.connection_frame.winfo_children():
            child.destroy()

        connections = (
            self.data.get_connections_for(
                self.person.id
            )
        )

        # ---------------------------------------------------------
        # Bestehende Verbindungen
        # ---------------------------------------------------------

        for connection in connections:

            label, other_id = (
                connection_description(
                    self.data,
                    connection,
                    self.person.id
                )
            )

            other = self.data.persons.get(
                other_id
            )

            if not other:
                continue

            self._connection_row(
                label,
                other,
                connection
            )

        # ---------------------------------------------------------
        # Kinderbereich
        # ---------------------------------------------------------

        ttk.Separator(
            self.connection_frame,
            orient="horizontal"
        ).pack(
            fill="x",
            pady=8
        )

        ttk.Label(
            self.connection_frame,
            text="Weitere Kinder hinzufügen"
        ).pack(
            anchor="w",
            pady=(0, 4)
        )

        self._add_empty_child_row()

    def _connection_row(
        self,
        label,
        person,
        connection
    ):

        row = ttk.Frame(
            self.connection_frame
        )

        row.pack(
            fill="x",
            pady=2
        )

        ttk.Label(
            row,
            text=label,
            width=20
        ).pack(
            side="left"
        )

        ttk.Label(
            row,
            text=person.display_name()
        ).pack(
            side="left",
            fill="x",
            expand=True
        )

        ttk.Button(
            row,
            text="×",
            width=3,
            command=lambda c=connection:
                self.delete_connection(c)
        ).pack(
            side="right"
        )

    # =============================================================
    # Kinder-Zeile
    # =============================================================

    def _add_empty_child_row(self):

        row = ttk.Frame(
            self.connection_frame
        )

        row.pack(
            fill="x",
            pady=2
        )

        ttk.Label(
            row,
            text="Kind",
            width=20
        ).pack(
            side="left"
        )

        combo = ttk.Combobox(
            row,
            values=self._person_names(),
            width=42
        )

        combo.pack(
            side="left",
            fill="x",
            expand=True
        )

        def add_child():

            child = self._find_or_create(
                combo.get()
            )

            if not child:
                return

            add_parent_child(
                self.data,
                self.person.id,
                child.id
            )

            self._refresh_connections()

        ttk.Button(
            row,
            text="+",
            width=3,
            command=add_child
        ).pack(
            side="right",
            padx=(5, 0)
        )

        # Enter funktioniert ebenfalls.
        combo.bind(
            "<Return>",
            lambda event: add_child()
        )

    # =============================================================
    # Verbindung hinzufügen
    # =============================================================

    def add_connection(self):

        other = self._find_or_create(
            self.new_person.get()
        )

        if not other:
            return

        relation = (
            self.new_relation.get()
        )

        if relation == "Vater":
            add_parent_child(
                self.data,
                other.id,
                self.person.id
            )

        elif relation == "Mutter":
            add_parent_child(
                self.data,
                other.id,
                self.person.id
            )

        elif relation == "Kind":
            add_parent_child(
                self.data,
                self.person.id,
                other.id
            )

        elif relation == "Ehegatte/Ehegattin":
            add_spouse(
                self.data,
                self.person.id,
                other.id
            )

        self.new_person.set("")

        self._refresh_connections()

    # =============================================================
    # Verbindung löschen
    # =============================================================

    def delete_connection(
        self,
        connection
    ):

        self.data.disconnect(
            connection.source,
            connection.target,
            connection.relation
        )

        self._refresh_connections()

    # =============================================================
    # Speichern
    # =============================================================

    def save(self):

        old_family = self.person.family_name

        for key, variable in self.vars.items():

            setattr(
                self.person,
                key,
                variable.get().strip()
            )

        # Neue Familien automatisch registrieren.
        self.data.ensure_families_for_person(
            self.person
        )

        self.on_save()

        self.destroy()