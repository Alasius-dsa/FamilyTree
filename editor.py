from __future__ import annotations

import os
import tkinter as tk
from tkinter import ttk, messagebox
import webbrowser
from urllib.request import urlopen

from models import (
    FamilyTreeData,
    Person
)

from connections import (
    CONNECTION_WIDTH
)


BOX_W = 220
BOX_H = 110

MAX_BOX_WIDTH = BOX_W * 1.5

MIN_FONT_SIZE = 8
BASE_NAME_FONT_SIZE = 16


class TreeCanvas(tk.Canvas):

    def __init__(
        self,
        master,
        data: FamilyTreeData,
        on_edit,
        **kwargs
    ):

        super().__init__(
            master,
            background="#f4f4f4",
            highlightthickness=0,
            **kwargs
        )

        self.data = data
        self.on_edit = on_edit

        self.zoom = 1.0

        self.drag_id = None

        self.drag_offset = (
            0,
            0
        )

        self.background_image = None
        self.background_photo = None

        self.bind(
            "<ButtonPress-1>",
            self._press
        )

        self.bind(
            "<B1-Motion>",
            self._drag
        )

        self.bind(
            "<ButtonRelease-1>",
            self._release
        )

        self.bind(
            "<Button-3>",
            self._right_click
        )

        self.bind(
            "<Double-Button-1>",
            self._double_click
        )

        self.bind(
            "<MouseWheel>",
            self._wheel
        )

        self.bind(
            "<Configure>",
            self._on_resize
        )

        self.redraw()

    # =============================================================
    # Zeichnen
    # =============================================================

    def redraw(self):

        self.delete("all")

        self._draw_background()

        self._draw_connections()

        self._draw_persons()

    # =============================================================
    # Hintergrund
    # =============================================================

    def _draw_background(self):

        source = self.data.background.source

        if not source:
            return

        try:
            from PIL import Image, ImageTk

            image = self._load_background_image(
                source
            )

            if image is None:
                return

            canvas_width = max(
                1,
                self.winfo_width()
            )

            canvas_height = max(
                1,
                self.winfo_height()
            )

            if self.data.background.mode == "stretch":

                image = image.resize(
                    (
                        canvas_width,
                        canvas_height
                    )
                )

                self.background_photo = ImageTk.PhotoImage(
                    image
                )

                self.create_image(
                    0,
                    0,
                    anchor="nw",
                    image=self.background_photo,
                    tags="background"
                )

            else:

                # Tile
                tile = image

                # Genug große Fläche erzeugen.
                result = Image.new(
                    "RGB",
                    (
                        canvas_width,
                        canvas_height
                    )
                )

                for x in range(
                    0,
                    canvas_width,
                    tile.width
                ):
                    for y in range(
                        0,
                        canvas_height,
                        tile.height
                    ):

                        result.paste(
                            tile,
                            (
                                x,
                                y
                            )
                        )

                self.background_photo = ImageTk.PhotoImage(
                    result
                )

                self.create_image(
                    0,
                    0,
                    anchor="nw",
                    image=self.background_photo,
                    tags="background"
                )

            self.tag_lower(
                "background"
            )

        except ImportError:

            self.create_text(
                20,
                20,
                anchor="nw",
                text=(
                    "Für Bildhintergründe wird "
                    "Pillow benötigt:\n"
                    "pip install pillow"
                ),
                fill="#aa0000",
                tags="background"
            )

    def _load_background_image(
        self,
        source
    ):

        from PIL import Image
        from io import BytesIO

        # HTTP / HTTPS
        if source.startswith(
            "http://"
        ) or source.startswith(
            "https://"
        ):

            with urlopen(
                source,
                timeout=10
            ) as response:

                data = response.read()

            return Image.open(
                BytesIO(data)
            ).convert(
                "RGB"
            )

        # Lokale Datei
        if os.path.isfile(source):

            return Image.open(
                source
            ).convert(
                "RGB"
            )

        return None

    def _on_resize(
        self,
        event
    ):

        self.redraw()

    # =============================================================
    # Verbindungen
    # =============================================================

    def _draw_connections(self):

        for connection in self.data.connections:

            source = self.data.persons.get(
                connection.source
            )

            target = self.data.persons.get(
                connection.target
            )

            if not source or not target:
                continue

            if connection.relation == "spouse":

                self._draw_spouse_connection(
                    source,
                    target
                )

            else:

                self._draw_parent_connection(
                    source,
                    target
                )

    def _draw_parent_connection(
        self,
        source,
        target
    ):

        ax = source.x + self._box_width(
            source
        ) / 2

        ay = source.y + BOX_H

        bx = target.x + self._box_width(
            target
        ) / 2

        by = target.y

        mid_y = (ay + by) / 2

        points = [
            (
                ax,
                ay
            ),
            (
                ax,
                mid_y
            ),
            (
                bx,
                mid_y
            ),
            (
                bx,
                by
            )
        ]

        self._draw_polyline(
            points,
            dashed=False
        )

    def _draw_spouse_connection(
        self,
        source,
        target
    ):

        ax = source.x + self._box_width(
            source
        )

        ay = source.y + BOX_H / 2

        bx = target.x

        by = target.y + BOX_H / 2

        mid_x = (ax + bx) / 2

        points = [
            (
                ax,
                ay
            ),
            (
                mid_x,
                ay
            ),
            (
                mid_x,
                by
            ),
            (
                bx,
                by
            )
        ]

        self._draw_polyline(
            points,
            dashed=True
        )

    def _draw_polyline(
        self,
        points,
        dashed=False
    ):

        flattened = []

        for x, y in points:

            flattened.extend(
                [
                    x * self.zoom,
                    y * self.zoom
                ]
            )

        kwargs = {
            "fill": "#333333",
            "width": CONNECTION_WIDTH
        }

        if dashed:
            kwargs["dash"] = (
                10,
                7
            )

        self.create_line(
            *flattened,
            **kwargs,
            tags="connection"
        )

    # =============================================================
    # Box width / text size
    # =============================================================

    def _box_width(
        self,
        person: Person
    ) -> float:

        first = person.first_name or ""
        family = person.family_name or ""

        longest = max(
            len(first),
            len(family),
            1
        )

        # Näherungsweise benötigte Breite.
        required = (
            longest * 9
            + 30
        )

        return min(
            MAX_BOX_WIDTH,
            max(
                BOX_W,
                required
            )
        )

    def _font_size(
        self,
        person: Person
    ) -> int:

        width = self._box_width(
            person
        )

        longest = max(
            len(person.first_name or ""),
            len(person.family_name or ""),
            1
        )

        available = width - 20

        estimated_text_width = (
            longest
            * BASE_NAME_FONT_SIZE
            * 0.58
        )

        if estimated_text_width <= available:
            return BASE_NAME_FONT_SIZE

        size = (
            BASE_NAME_FONT_SIZE
            * available
            / estimated_text_width
        )

        return max(
            MIN_FONT_SIZE,
            int(size)
        )

    # =============================================================
    # Personen
    # =============================================================

    def _draw_persons(self):

        for person in self.data.persons.values():

            self._draw_person(
                person
            )

    def _draw_person(
        self,
        person
    ):

        x = person.x * self.zoom
        y = person.y * self.zoom

        width = (
            self._box_width(person)
            * self.zoom
        )

        height = (
            BOX_H
            * self.zoom
        )

        colors = self.data.get_family_colors(
            person.family_name
        )

        tag = f"person:{person.id}"

        # ---------------------------------------------------------
        # Hausfarben
        # ---------------------------------------------------------

        if len(colors) == 1:

            self.create_rectangle(
                x,
                y,
                x + width,
                y + height,
                fill=colors[0],
                outline="#222222",
                width=2,
                tags=tag
            )

        else:

            stripe_width = (
                width / len(colors)
            )

            for index, color in enumerate(
                colors
            ):

                self.create_rectangle(
                    x + index * stripe_width,
                    y,
                    x + (
                        index + 1
                    ) * stripe_width + 1,
                    y + height,
                    fill=color,
                    outline="",
                    tags=tag
                )

            self.create_rectangle(
                x,
                y,
                x + width,
                y + height,
                fill="",
                outline="#222222",
                width=2,
                tags=tag
            )

        # ---------------------------------------------------------
        # Name
        # ---------------------------------------------------------

        font_size = self._font_size(
            person
        )

        self.create_text(
            x + 10 * self.zoom,
            y + 25 * self.zoom,
            anchor="w",
            text=person.first_name,
            font=(
                "Arial",
                max(
                    MIN_FONT_SIZE,
                    int(font_size * self.zoom)
                ),
                "bold"
            ),
            tags=tag
        )

        self.create_text(
            x + 10 * self.zoom,
            y + 48 * self.zoom,
            anchor="w",
            text=person.family_name,
            font=(
                "Arial",
                max(
                    MIN_FONT_SIZE,
                    int(font_size * self.zoom)
                )
            ),
            tags=tag
        )

        # ---------------------------------------------------------
        # Geburtsdatum
        # ---------------------------------------------------------

        self.create_text(
            x + 10 * self.zoom,
            y + 73 * self.zoom,
            anchor="w",
            text=(
                f"Geb.: "
                f"{person.birth_date or '—'}"
            ),
            font=(
                "Arial",
                max(
                    7,
                    int(11 * self.zoom)
                )
            ),
            tags=tag
        )

        # ---------------------------------------------------------
        # Todesdatum
        # ---------------------------------------------------------

        self.create_text(
            x + 10 * self.zoom,
            y + 92 * self.zoom,
            anchor="w",
            text=(
                f"Tod: "
                f"{person.death_date or '—'}"
            ),
            font=(
                "Arial",
                max(
                    7,
                    int(11 * self.zoom)
                )
            ),
            tags=tag
        )

        # ---------------------------------------------------------
        # Welt-Symbol
        # ---------------------------------------------------------

        if person.link:

            self.create_text(
                x + width - 17 * self.zoom,
                y + 17 * self.zoom,
                text="🌐",
                font=(
                    "Arial",
                    max(
                        8,
                        int(13 * self.zoom)
                    )
                ),
                tags=tag
            )

    # =============================================================
    # Koordinaten
    # =============================================================

    def _person_at(
        self,
        event
    ):

        world_x = (
            event.x / self.zoom
        )

        world_y = (
            event.y / self.zoom
        )

        persons = list(
            self.data.persons.values()
        )

        for person in reversed(
            persons
        ):

            width = self._box_width(
                person
            )

            if (
                person.x
                <= world_x
                <= person.x + width
                and
                person.y
                <= world_y
                <= person.y + BOX_H
            ):
                return person

        return None

    # =============================================================
    # Drag & Drop
    # =============================================================

    def _press(
        self,
        event
    ):

        person = self._person_at(
            event
        )

        if not person:
            self.drag_id = None
            return

        self.drag_id = person.id

        world_x = (
            event.x / self.zoom
        )

        world_y = (
            event.y / self.zoom
        )

        self.drag_offset = (
            world_x - person.x,
            world_y - person.y
        )

    def _drag(
        self,
        event
    ):

        if not self.drag_id:
            return

        person = self.data.persons[
            self.drag_id
        ]

        world_x = (
            event.x / self.zoom
        )

        world_y = (
            event.y / self.zoom
        )

        person.x = max(
            0,
            world_x - self.drag_offset[0]
        )

        person.y = max(
            0,
            world_y - self.drag_offset[1]
        )

        self.redraw()

    def _release(
        self,
        event
    ):

        self.drag_id = None

    # =============================================================
    # Rechtsklick
    # =============================================================

    def _right_click(
        self,
        event
    ):

        person = self._person_at(
            event
        )

        if not person:
            return

        menu = tk.Menu(
            self,
            tearoff=False
        )

        menu.add_command(
            label="Editieren",
            command=lambda: self.on_edit(
                person
            )
        )

        if person.link:

            menu.add_command(
                label="Link öffnen",
                command=lambda: webbrowser.open(
                    person.link
                )
            )

        menu.add_separator()

        menu.add_command(
            label="Person löschen",
            command=lambda: self._delete_person(
                person
            )
        )

        try:

            menu.tk_popup(
                event.x_root,
                event.y_root
            )

        finally:

            menu.grab_release()

    def _double_click(
        self,
        event
    ):

        person = self._person_at(
            event
        )

        if person:

            self.on_edit(
                person
            )

    def _delete_person(
        self,
        person
    ):

        if not messagebox.askyesno(
            "Person löschen",
            (
                f"Soll {person.display_name()} "
                f"wirklich gelöscht werden?"
            )
        ):
            return

        self.data.remove_person(
            person.id
        )

        self.redraw()

    # =============================================================
    # Zoom
    # =============================================================

    def _wheel(
        self,
        event
    ):

        if event.delta > 0:
            factor = 1.1
        else:
            factor = 0.9

        self.zoom = min(
            3.0,
            max(
                0.25,
                self.zoom * factor
            )
        )

        self.redraw()


class SidePanel(ttk.Frame):

    def __init__(
        self,
        master,
        data: FamilyTreeData,
        refresh,
        **kwargs
    ):

        super().__init__(
            master,
            padding=8,
            **kwargs
        )

        self.data = data
        self.refresh = refresh

        # ---------------------------------------------------------
        # Personen
        # ---------------------------------------------------------

        ttk.Label(
            self,
            text="Stammbaum",
            font=(
                "Arial",
                15,
                "bold"
            )
        ).pack(
            anchor="w"
        )

        ttk.Button(
            self,
            text="+ Person hinzufügen",
            command=self.add_person
        ).pack(
            fill="x",
            pady=(8, 10)
        )

        ttk.Label(
            self,
            text="Personen",
            font=(
                "Arial",
                11,
                "bold"
            )
        ).pack(
            anchor="w"
        )

        self.listbox = tk.Listbox(
            self,
            height=12
        )

        self.listbox.pack(
            fill="both",
            expand=True
        )

        self.listbox.bind(
            "<Double-Button-1>",
            self.edit_selected
        )

        # ---------------------------------------------------------
        # Familien
        # ---------------------------------------------------------

        ttk.Label(
            self,
            text="Familien",
            font=(
                "Arial",
                11,
                "bold"
            )
        ).pack(
            anchor="w",
            pady=(12, 4)
        )

        self.family_listbox = tk.Listbox(
            self,
            height=8
        )

        self.family_listbox.pack(
            fill="both",
            expand=True
        )

        self.family_listbox.bind(
            "<Double-Button-1>",
            self.edit_family
        )

        self.family_listbox.bind(
            "<Button-3>",
            self.family_context_menu
        )

        ttk.Button(
            self,
            text="+ Familie hinzufügen",
            command=self.add_family
        ).pack(
            fill="x",
            pady=(5, 0)
        )

        # ---------------------------------------------------------
        # Hintergrund
        # ---------------------------------------------------------

        ttk.Label(
            self,
            text="Hintergrund",
            font=(
                "Arial",
                11,
                "bold"
            )
        ).pack(
            anchor="w",
            pady=(15, 4)
        )

        ttk.Button(
            self,
            text="Hintergrund einstellen",
            command=self.edit_background
        ).pack(
            fill="x"
        )

        self.update_list()

    # =============================================================
    # Personenliste
    # =============================================================

    def update_list(self):

        self.listbox.delete(
            0,
            "end"
        )

        for person in self.data.persons.values():

            self.listbox.insert(
                "end",
                person.display_name()
            )

        self.family_listbox.delete(
            0,
            "end"
        )

        for family in self.data.families.values():

            self.family_listbox.insert(
                "end",
                family.name
            )

    def add_person(self):

        import uuid

        person = Person(
            id=str(uuid.uuid4()),
            first_name="Neue",
            family_name="Person",
            x=100 + len(
                self.data.persons
            ) * 30,
            y=100 + len(
                self.data.persons
            ) * 30
        )

        self.data.add_person(
            person
        )

        self.refresh()

    def edit_selected(
        self,
        event=None
    ):

        selection = (
            self.listbox.curselection()
        )

        if not selection:
            return

        persons = list(
            self.data.persons.values()
        )

        person = persons[
            selection[0]
        ]

        self.master.master.open_editor(
            person
        )

    # =============================================================
    # Familien
    # =============================================================

    def add_family(self):

        FamilyDialog(
            self,
            self.data,
            None,
            self.refresh
        )

    def edit_family(
        self,
        event=None
    ):

        selection = (
            self.family_listbox.curselection()
        )

        if not selection:
            return

        families = list(
            self.data.families.values()
        )

        family = families[
            selection[0]
        ]

        FamilyDialog(
            self,
            self.data,
            family,
            self.refresh
        )

    def family_context_menu(
        self,
        event
    ):

        index = self.family_listbox.nearest(
            event.y
        )

        if index < 0:
            return

        self.family_listbox.selection_clear(
            0,
            "end"
        )

        self.family_listbox.selection_set(
            index
        )

        families = list(
            self.data.families.values()
        )

        if index >= len(families):
            return

        family = families[index]

        menu = tk.Menu(
            self,
            tearoff=False
        )

        menu.add_command(
            label="Editieren",
            command=lambda: FamilyDialog(
                self,
                self.data,
                family,
                self.refresh
            )
        )

        menu.add_command(
            label="Löschen",
            command=lambda: self.delete_family(
                family.name
            )
        )

        try:

            menu.tk_popup(
                event.x_root,
                event.y_root
            )

        finally:

            menu.grab_release()

    def delete_family(
        self,
        name
    ):

        if not messagebox.askyesno(
            "Familie löschen",
            (
                f"Familie '{name}' löschen?\n\n"
                "Die Personen behalten ihren "
                "Familiennamen. Die Farbe wird "
                "jedoch entfernt."
            )
        ):
            return

        self.data.remove_family(
            name
        )

        self.refresh()

    # =============================================================
    # Hintergrund
    # =============================================================

    def edit_background(self):

        BackgroundDialog(
            self,
            self.data,
            self.refresh
        )


class FamilyDialog(tk.Toplevel):

    def __init__(
        self,
        master,
        data,
        family,
        refresh
    ):

        super().__init__(
            master
        )

        self.title(
            "Familie bearbeiten"
            if family
            else
            "Neue Familie"
        )

        self.geometry(
            "450x230"
        )

        self.data = data
        self.family = family
        self.refresh = refresh

        frame = ttk.Frame(
            self,
            padding=15
        )

        frame.pack(
            fill="both",
            expand=True
        )

        ttk.Label(
            frame,
            text="Familienname"
        ).grid(
            row=0,
            column=0,
            sticky="w",
            pady=5
        )

        self.name_var = tk.StringVar(
            value=family.name
            if family
            else ""
        )

        ttk.Entry(
            frame,
            textvariable=self.name_var,
            width=35
        ).grid(
            row=0,
            column=1,
            sticky="ew"
        )

        ttk.Label(
            frame,
            text="Farbe"
        ).grid(
            row=1,
            column=0,
            sticky="w",
            pady=5
        )

        self.color_var = tk.StringVar(
            value=family.color
            if family
            else "#ffffff"
        )

        ttk.Entry(
            frame,
            textvariable=self.color_var,
            width=20
        ).grid(
            row=1,
            column=1,
            sticky="w"
        )

        ttk.Button(
            frame,
            text="Farbe auswählen",
            command=self.choose_color
        ).grid(
            row=2,
            column=1,
            sticky="w",
            pady=5
        )

        buttons = ttk.Frame(
            frame
        )

        buttons.grid(
            row=3,
            column=0,
            columnspan=2,
            sticky="e",
            pady=15
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
            padx=5
        )

        frame.columnconfigure(
            1,
            weight=1
        )

        self.transient(
            master
        )

        self.grab_set()

    def choose_color(self):

        from tkinter import colorchooser

        color = colorchooser.askcolor(
            initialcolor=self.color_var.get()
        )[1]

        if color:
            self.color_var.set(
                color
            )

    def save(self):

        name = self.name_var.get().strip()

        if not name:
            messagebox.showerror(
                "Fehler",
                "Der Familienname darf nicht leer sein."
            )
            return

        if self.family:

            old_name = self.family.name

            self.data.rename_family(
                old_name,
                name
            )

            self.data.families[
                name
            ].color = self.color_var.get()

        else:

            self.data.families[
                name
            ] = self.data.families.get(
                name
            ) or __import__(
                "models"
            ).Family(
                name=name,
                color=self.color_var.get()
            )

        self.refresh()

        self.destroy()


class BackgroundDialog(tk.Toplevel):

    def __init__(
        self,
        master,
        data,
        refresh
    ):

        super().__init__(
            master
        )

        self.title(
            "Hintergrund"
        )

        self.geometry(
            "650x260"
        )

        self.data = data
        self.refresh = refresh

        frame = ttk.Frame(
            self,
            padding=15
        )

        frame.pack(
            fill="both",
            expand=True
        )

        ttk.Label(
            frame,
            text=(
                "Bildquelle\n"
                "Lokaler Pfad oder HTTP(S)-Link"
            )
        ).grid(
            row=0,
            column=0,
            sticky="nw",
            pady=5
        )

        self.source_var = tk.StringVar(
            value=data.background.source
        )

        ttk.Entry(
            frame,
            textvariable=self.source_var,
            width=55
        ).grid(
            row=0,
            column=1,
            sticky="ew"
        )

        ttk.Button(
            frame,
            text="Datei auswählen",
            command=self.choose_file
        ).grid(
            row=1,
            column=1,
            sticky="w",
            pady=5
        )

        ttk.Label(
            frame,
            text="Darstellung"
        ).grid(
            row=2,
            column=0,
            sticky="w",
            pady=10
        )

        self.mode_var = tk.StringVar(
            value=data.background.mode
        )

        ttk.Radiobutton(
            frame,
            text="Kacheln",
            variable=self.mode_var,
            value="tile"
        ).grid(
            row=2,
            column=1,
            sticky="w"
        )

        ttk.Radiobutton(
            frame,
            text="Auf sichtbaren Bereich strecken",
            variable=self.mode_var,
            value="stretch"
        ).grid(
            row=3,
            column=1,
            sticky="w"
        )

        buttons = ttk.Frame(
            frame
        )

        buttons.grid(
            row=5,
            column=0,
            columnspan=2,
            sticky="e",
            pady=15
        )

        ttk.Button(
            buttons,
            text="Hintergrund entfernen",
            command=self.remove_background
        ).pack(
            side="left",
            padx=5
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
            padx=5
        )

        frame.columnconfigure(
            1,
            weight=1
        )

        self.transient(
            master
        )

        self.grab_set()

    def choose_file(self):

        from tkinter import filedialog

        path = filedialog.askopenfilename(
            title="Hintergrundbild auswählen",
            filetypes=[
                (
                    "Bilder",
                    "*.png *.jpg *.jpeg *.gif *.bmp *.webp"
                ),
                (
                    "Alle Dateien",
                    "*.*"
                )
            ]
        )

        if path:
            self.source_var.set(
                path
            )

    def save(self):

        self.data.background.source = (
            self.source_var.get().strip()
        )

        self.data.background.mode = (
            self.mode_var.get()
        )

        self.refresh()

        self.destroy()

    def remove_background(self):

        self.data.background.source = ""

        self.refresh()

        self.destroy()