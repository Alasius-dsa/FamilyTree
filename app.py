from __future__ import annotations

import tkinter as tk
from tkinter import ttk, filedialog, messagebox

from models import (
    FamilyTreeData,
    Person
)

from editor import (
    TreeCanvas,
    SidePanel
)

from dialogs import (
    PersonDialog
)

from svg_export import (
    export_svg
)


class FamilyTreeApp:

    def __init__(self):

        self.root = tk.Tk()

        self.root.title(
            "Fantasy Family Tree"
        )

        self.root.geometry(
            "1400x850"
        )

        self.data = FamilyTreeData()

        self._build_ui()

    # =============================================================
    # UI
    # =============================================================

    def _build_ui(self):

        toolbar = ttk.Frame(
            self.root,
            padding=5
        )

        toolbar.pack(
            side="top",
            fill="x"
        )

        ttk.Button(
            toolbar,
            text="Neu",
            command=self.new_tree
        ).pack(
            side="left"
        )

        ttk.Button(
            toolbar,
            text="Öffnen",
            command=self.load
        ).pack(
            side="left",
            padx=4
        )

        ttk.Button(
            toolbar,
            text="Speichern",
            command=self.save
        ).pack(
            side="left"
        )

        ttk.Button(
            toolbar,
            text="SVG exportieren",
            command=self.export
        ).pack(
            side="left",
            padx=4
        )

        ttk.Button(
            toolbar,
            text="Panel ein-/ausblenden",
            command=self.toggle_panel
        ).pack(
            side="left",
            padx=12
        )

        ttk.Button(
            toolbar,
            text="Person hinzufügen",
            command=self.add_person
        ).pack(
            side="right"
        )

        # ---------------------------------------------------------
        # Hauptbereich
        # ---------------------------------------------------------

        self.main = ttk.Frame(
            self.root
        )

        self.main.pack(
            fill="both",
            expand=True
        )

        # ---------------------------------------------------------
        # Sidepanel
        # ---------------------------------------------------------

        self.panel_visible = True

        self.panel = SidePanel(
            self.main,
            self.data,
            self.refresh
        )

        self.panel.pack(
            side="left",
            fill="y"
        )

        # ---------------------------------------------------------
        # Canvas
        # ---------------------------------------------------------

        self.canvas = TreeCanvas(
            self.main,
            self.data,
            self.open_editor
        )

        self.canvas.pack(
            side="left",
            fill="both",
            expand=True
        )

        # Explicit reference; do not depend on the Tk parent hierarchy.
        self.panel.canvas = self.canvas

    # =============================================================
    # Aktualisieren
    # =============================================================

    def refresh(self):

        self.panel.data = self.data
        self.canvas.data = self.data

        self.panel.update_list()

        self.canvas.redraw()

    # =============================================================
    # Panel
    # =============================================================

    def toggle_panel(self):

        if self.panel_visible:

            self.panel.pack_forget()

        else:

            self.panel.pack(
                side="left",
                fill="y",
                before=self.canvas
            )

        self.panel_visible = (
            not self.panel_visible
        )

    # =============================================================
    # Person
    # =============================================================

    def add_person(self):

        import uuid

        person = Person(
            id=str(uuid.uuid4()),
            first_name="Neue",
            family_name="Person",
            x=100,
            y=100
        )

        self.data.add_person(
            person
        )

        self.refresh()

        self.open_editor(
            person
        )

    def open_editor(
        self,
        person
    ):

        PersonDialog(
            self.root,
            self.data,
            person,
            self.refresh
        )

    # =============================================================
    # Neu
    # =============================================================

    def new_tree(self):

        if not messagebox.askyesno(
            "Neuer Stammbaum",
            "Aktuellen Stammbaum verwerfen?"
        ):
            return

        self.data = FamilyTreeData()

        self.refresh()

    # =============================================================
    # Speichern
    # =============================================================

    def save(self):

        path = filedialog.asksaveasfilename(
            title="Stammbaum speichern",
            defaultextension=".json",
            filetypes=[
                (
                    "Family Tree JSON",
                    "*.json"
                )
            ]
        )

        if not path:
            return

        try:

            self.data.save(
                path
            )

        except Exception as exc:

            messagebox.showerror(
                "Fehler",
                f"Speichern fehlgeschlagen:\n\n{exc}"
            )

    # =============================================================
    # Laden
    # =============================================================

    def load(self):

        path = filedialog.askopenfilename(
            title="Stammbaum öffnen",
            filetypes=[
                (
                    "Family Tree JSON",
                    "*.json"
                )
            ]
        )

        if not path:
            return

        try:

            self.data = (
                FamilyTreeData.load(
                    path
                )
            )

            self.refresh()

        except Exception as exc:

            messagebox.showerror(
                "Fehler",
                f"Laden fehlgeschlagen:\n\n{exc}"
            )

    # =============================================================
    # SVG
    # =============================================================

    def export(self):

        path = filedialog.asksaveasfilename(
            title="SVG exportieren",
            defaultextension=".svg",
            filetypes=[
                (
                    "SVG",
                    "*.svg"
                )
            ]
        )

        if not path:
            return

        try:

            export_svg(
                self.data,
                path
            )

            messagebox.showinfo(
                "Export",
                "SVG wurde erfolgreich exportiert."
            )

        except Exception as exc:

            messagebox.showerror(
                "Exportfehler",
                f"SVG konnte nicht exportiert werden:\n\n{exc}"
            )

    # =============================================================
    # Start
    # =============================================================

    def run(self):

        self.root.mainloop()