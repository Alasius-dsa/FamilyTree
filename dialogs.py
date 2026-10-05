from __future__ import annotations
import tkinter as tk
from tkinter import ttk, colorchooser, messagebox, filedialog
from pathlib import Path
from models import FamilyTreeData,Person,Family
from connections import connection_description,add_parent_child,add_spouse
from calendar_system import CalendarDefinition,load_calendars,calendar_directory,get_calendar

class DateWidget(ttk.Frame):
    def __init__(self,master,calendar_id="",value=None):
        super().__init__(master)
        self.calendar_var=tk.StringVar(value=calendar_id); self.day=tk.StringVar(); self.month=tk.StringVar(); self.year=tk.StringVar()
        self.combo=ttk.Combobox(self,textvariable=self.calendar_var,state="readonly",width=18); self.combo.pack(side="left")
        self.daybox=ttk.Combobox(self,textvariable=self.day,width=4); self.daybox.pack(side="left",padx=3)
        self.monthbox=ttk.Combobox(self,textvariable=self.month,width=14,state="readonly"); self.monthbox.pack(side="left")
        ttk.Entry(self,textvariable=self.year,width=8).pack(side="left",padx=3)
        self.refresh_calendars()
        self.combo.bind("<<ComboboxSelected>>",lambda e:self._refresh_months())
        if isinstance(value,dict):
            self.calendar_var.set(value.get("calendar_id","")); self.day.set(str(value.get("day",""))); self.year.set(str(value.get("year","")))
            self._refresh_months(); self.month.set(str(value.get("month","")))
        elif isinstance(value,str) and value:
            self._parse_string(value)
    def refresh_calendars(self):
        self.cals=load_calendars(); self.labels=[c.name for c in self.cals.values()]
        self.combo["values"]=self.labels
        if self.calendar_var.get() in self.cals:return
        if self.labels:self.calendar_var.set(self.labels[0])
        self._refresh_months()
    def _selected(self):
        for c in self.cals.values():
            if c.id==self.calendar_var.get() or c.name==self.calendar_var.get():return c
        return None
    def _refresh_months(self):
        c=self._selected(); self.monthbox["values"]=c.month_names() if c else []
    def _parse_string(self,s):
        for c in self.cals.values():
            parsed=c.parse_date(s)
            if parsed:
                self.calendar_var.set(c.name); self._refresh_months(); self.day.set(str(parsed[0])); self.month.set(str(parsed[1])); self.year.set(str(parsed[2])); return
    def get(self):
        c=self._selected()
        if not c or not self.day.get() or not self.month.get() or not self.year.get():return ""
        try: day,year=int(self.day.get()),int(self.year.get())
        except ValueError:return ""
        try: month=self.monthbox["values"].index(self.month.get())+1
        except ValueError:
            try: month=int(self.month.get())
            except ValueError:return ""
        if not 1<=day<=c.month_days(month):return ""
        return {"calendar_id":c.id,"day":day,"month":month,"year":year}
    def text(self):
        v=self.get()
        if not v:return ""
        c=get_calendar(v["calendar_id"]); return c.format_date(v["day"],v["month"],v["year"]) if c else ""

class PersonDialog(tk.Toplevel):
    def __init__(self,master,data,person,on_save):
        super().__init__(master); self.title(f"Person bearbeiten – {person.display_name()}"); self.geometry("850x780"); self.data=data; self.person=person; self.on_save=on_save; self._build_ui(); self._refresh_connections()
    def _build_ui(self):
        outer=ttk.Frame(self,padding=14); outer.pack(fill="both",expand=True)
        ttk.Label(outer,text="Person",font=("Arial",14,"bold")).pack(anchor="w")
        basic=ttk.Frame(outer); basic.pack(fill="x",pady=10); self.vars={}
        for row,(label,key) in enumerate([("Vorname","first_name"),("Namenspräfix","name_prefix"),("Familienname","family_name"),("Link","link")]):
            ttk.Label(basic,text=label).grid(row=row,column=0,sticky="w",pady=3); v=tk.StringVar(value=getattr(self.person,key,"")); self.vars[key]=v; ttk.Entry(basic,textvariable=v,width=60).grid(row=row,column=1,sticky="ew",padx=8)
        ttk.Label(basic,text="Geburtsdatum").grid(row=4,column=0,sticky="w",pady=3); self.birth=DateWidget(basic,value=self.person.birth_date); self.birth.grid(row=4,column=1,sticky="w",padx=8)
        ttk.Label(basic,text="Todesdatum").grid(row=5,column=0,sticky="w",pady=3); self.death=DateWidget(basic,value=self.person.death_date); self.death.grid(row=5,column=1,sticky="w",padx=8)
        ttk.Label(outer,text="Schnelleingabe: z.B. 12.3.1024 oder 12. Praios 1024 BF; wird beim Speichern in den gewählten Kalender übernommen.",wraplength=700).pack(anchor="w")
        self.quick_birth=tk.StringVar(); self.quick_death=tk.StringVar()
        # The dedicated widgets remain authoritative; quick fields are accepted if filled.
        for label,var in [("Geburt schnell",self.quick_birth),("Tod schnell",self.quick_death)]:
            f=ttk.Frame(outer); f.pack(fill="x",pady=2); ttk.Label(f,text=label,width=18).pack(side="left"); ttk.Entry(f,textvariable=var,width=50).pack(side="left")
        ttk.Label(outer,text="Verbindungen",font=("Arial",12,"bold")).pack(anchor="w",pady=(15,5))
        self.connection_frame=ttk.Frame(outer); self.connection_frame.pack(fill="both",expand=True)
        new=ttk.Frame(outer); new.pack(fill="x",pady=8); self.new_relation=tk.StringVar(value="Kind")
        ttk.Combobox(new,textvariable=self.new_relation,values=["Vater","Mutter","Kind","Ehegatte/Ehegattin"],state="readonly",width=20).pack(side="left")
        self.new_person=ttk.Combobox(new,values=self._person_names(),width=42); self.new_person.pack(side="left",padx=8,fill="x",expand=True); ttk.Button(new,text="Hinzufügen",command=self.add_connection).pack(side="left")
        buttons=ttk.Frame(outer); buttons.pack(fill="x"); ttk.Button(buttons,text="Abbrechen",command=self.destroy).pack(side="right"); ttk.Button(buttons,text="Speichern",command=self.save).pack(side="right",padx=8)
        basic.columnconfigure(1,weight=1)
    def _person_names(self):return [p.display_name() for p in self.data.persons.values() if p.id!=self.person.id]
    def _find_or_create(self,name):
        name=name.strip()
        if not name:return None
        for p in self.data.persons.values():
            if p.display_name().lower()==name.lower():return p
        parts=name.split(); p=Person(id=__import__("uuid").uuid4().hex,first_name=parts[0],family_name=parts[-1] if len(parts)>1 else ""); self.data.add_person(p); return p
    def _refresh_connections(self):
        for w in self.connection_frame.winfo_children():w.destroy()
        for c in self.data.get_connections_for(self.person.id):
            label,oid=connection_description(self.data,c,self.person.id); other=self.data.persons.get(oid)
            if other:
                r=ttk.Frame(self.connection_frame); r.pack(fill="x"); ttk.Label(r,text=label,width=20).pack(side="left"); ttk.Label(r,text=other.display_name()).pack(side="left",fill="x",expand=True); ttk.Button(r,text="×",width=3,command=lambda c=c:self.delete_connection(c)).pack(side="right")
    def add_connection(self):
        other=self._find_or_create(self.new_person.get())
        if not other:return
        r=self.new_relation.get()
        if r in ("Vater","Mutter"):add_parent_child(self.data,other.id,self.person.id)
        elif r=="Kind":add_parent_child(self.data,self.person.id,other.id)
        else:add_spouse(self.data,self.person.id,other.id)
        self.new_person.set(""); self._refresh_connections()
    def delete_connection(self,c):self.data.disconnect(c.source,c.target,c.relation); self._refresh_connections()
    def save(self):
        for k,v in self.vars.items():setattr(self.person,k,v.get().strip())
        for widget,var in ((self.birth,self.quick_birth),(self.death,self.quick_death)):
            if var.get().strip():
                parsed=None
                for c in load_calendars().values():
                    x=c.parse_date(var.get())
                    if x: parsed={"calendar_id":c.id,"day":x[0],"month":x[1],"year":x[2]}; break
                setattr(self.person,"birth_date" if widget is self.birth else "death_date",parsed or var.get().strip())
            else:setattr(self.person,"birth_date" if widget is self.birth else "death_date",widget.get())
        self.data.ensure_families_for_person(self.person); self.on_save(); self.destroy()

class FamilyDialog(tk.Toplevel):
    def __init__(self,master,data,family,refresh):
        super().__init__(master); self.data=data; self.family=family; self.refresh=refresh; self.title("Familie bearbeiten"); self.geometry("450x220")
        f=ttk.Frame(self,padding=15); f.pack(fill="both",expand=True); ttk.Label(f,text="Familienname").grid(row=0,column=0,sticky="w"); self.name=tk.StringVar(value=family.name if family else ""); ttk.Entry(f,textvariable=self.name,width=30).grid(row=0,column=1)
        ttk.Label(f,text="Farbe").grid(row=1,column=0,sticky="w"); self.color=tk.StringVar(value=family.color if family else "#ffffff"); ttk.Entry(f,textvariable=self.color,width=20).grid(row=1,column=1,sticky="w"); ttk.Button(f,text="Farbe auswählen",command=self.choose).grid(row=2,column=1,sticky="w")
        ttk.Button(f,text="Speichern",command=self.save).grid(row=3,column=1,sticky="e",pady=15)
    def choose(self):
        c=colorchooser.askcolor(initialcolor=self.color.get())[1]
        if c:self.color.set(c)
    def save(self):
        n=self.name.get().strip()
        if not n:return
        if self.family:self.data.rename_family(self.family.name,n);self.data.families[n].color=self.color.get()
        else:self.data.families[n]=Family(n,self.color.get())
        self.refresh();self.destroy()

class BackgroundDialog(tk.Toplevel):
    def __init__(self,master,data,refresh):
        super().__init__(master); self.data=data; self.refresh=refresh; self.title("Hintergrund"); self.geometry("700x240")
        f=ttk.Frame(self,padding=15); f.pack(fill="both",expand=True); ttk.Label(f,text="Bildquelle (Datei oder HTTP(S)-URL)").grid(row=0,column=0,sticky="w"); self.source=tk.StringVar(value=data.background.source); ttk.Entry(f,textvariable=self.source,width=60).grid(row=0,column=1)
        ttk.Button(f,text="Datei auswählen",command=self.file).grid(row=1,column=1,sticky="w")
        self.mode=tk.StringVar(value=data.background.mode); ttk.Radiobutton(f,text="Kacheln",variable=self.mode,value="tile").grid(row=2,column=1,sticky="w"); ttk.Radiobutton(f,text="Strecken",variable=self.mode,value="stretch").grid(row=3,column=1,sticky="w")
        ttk.Button(f,text="Entfernen",command=self.remove).grid(row=4,column=0,pady=15); ttk.Button(f,text="Speichern",command=self.save).grid(row=4,column=1,sticky="e")
    def file(self):
        p=filedialog.askopenfilename(filetypes=[("Bilder","*.png *.jpg *.jpeg *.gif *.bmp *.webp"),("Alle","*.*")])
        if p:self.source.set(p)
    def save(self):
        self.data.background.source=self.source.get().strip(); self.data.background.mode=self.mode.get(); self.refresh(); self.destroy()
    def remove(self):self.data.background.source="";self.refresh();self.destroy()

class CalendarManagerDialog(tk.Toplevel):
    def __init__(self,master,refresh):
        super().__init__(master); self.refresh=refresh; self.title("Kalender verwalten"); self.geometry("850x600"); self.cals=load_calendars()
        left=ttk.Frame(self,padding=10); left.pack(side="left",fill="y"); self.list=tk.Listbox(left,width=28); self.list.pack(fill="y",expand=True); self.list.bind("<<ListboxSelect>>",lambda e:self.load_selected()); self.rebuild_list()
        right=ttk.Frame(self,padding=10); right.pack(side="left",fill="both",expand=True); self.name=tk.StringVar(); self.era=tk.StringVar(); self.abbr=tk.StringVar()
        for r,(lab,var) in enumerate([("Name",self.name),("Jahresdefinition",self.era),("Kürzel",self.abbr)]):ttk.Label(right,text=lab).grid(row=r,column=0,sticky="w");ttk.Entry(right,textvariable=var,width=35).grid(row=r,column=1,sticky="w")
        ttk.Label(right,text="Monate").grid(row=3,column=0,sticky="nw"); self.month_frame=ttk.Frame(right);self.month_frame.grid(row=3,column=1,sticky="nsew"); right.rowconfigure(3,weight=1)
        ttk.Button(right,text="+ Monat",command=self.add_month).grid(row=4,column=1,sticky="w"); ttk.Button(right,text="Neuer Kalender",command=self.new_calendar).grid(row=5,column=0,pady=12); ttk.Button(right,text="Speichern",command=self.save).grid(row=5,column=1,sticky="e")
        self.new_calendar()
    def rebuild_list(self):
        self.list.delete(0,"end")
        for c in self.cals.values():self.list.insert("end",c.name)
    def clear_months(self):
        for w in self.month_frame.winfo_children():w.destroy()
        self.month_rows=[]
    def add_month(self,name="",days=30):
        row=ttk.Frame(self.month_frame);row.pack(fill="x",pady=1); n=tk.StringVar(value=name);d=tk.StringVar(value=str(days)); ttk.Entry(row,textvariable=n,width=28).pack(side="left");ttk.Entry(row,textvariable=d,width=7).pack(side="left",padx=5);ttk.Button(row,text="×",command=row.destroy).pack(side="left"); self.month_rows.append((row,n,d))
    def new_calendar(self):
        self.current_id=None;self.name.set("");self.era.set("");self.abbr.set("");self.clear_months()
        for _ in range(12):self.add_month("",30)
    def load_selected(self):
        s=self.list.curselection()
        if not s:return
        c=list(self.cals.values())[s[0]];self.current_id=c.id;self.name.set(c.name);self.era.set(c.era_name);self.abbr.set(c.era_abbreviation);self.clear_months()
        for m in c.months:self.add_month(m.get("name",""),m.get("days",30))
    def save(self):
        name=self.name.get().strip()
        if not name:return
        import re
        cid=self.current_id or re.sub(r"[^a-z0-9_-]+","_",name.lower()).strip("_") or "calendar"
        months=[]
        for row,n,d in self.month_rows:
            if not row.winfo_exists():continue
            try:days=int(d.get())
            except ValueError:continue
            if n.get().strip() and days>0:months.append({"name":n.get().strip(),"days":days})
        c=CalendarDefinition(cid,name,months,self.era.get().strip(),self.abbr.get().strip());c.save(calendar_directory()/f"{cid}.json");self.cals[cid]=c;self.rebuild_list();self.refresh()
