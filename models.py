from __future__ import annotations
from dataclasses import dataclass,field
from typing import Optional
import json
from pathlib import Path

@dataclass
class CalendarDate:
    calendar_id:str
    day:int
    month:int
    year:int
    def to_dict(self):return vars(self).copy()

@dataclass
class Person:
    id:str
    first_name:str=""
    name_prefix:str=""
    family_name:str=""
    birth_date:str|dict=""
    death_date:str|dict=""
    link:str=""
    x:float=100.0
    y:float=100.0
    def display_name(self):
        return " ".join(p for p in (self.first_name,self.name_prefix,self.family_name) if p).strip() or "(Unbenannt)"

@dataclass
class Family:
    name:str
    color:str="#ffffff"

@dataclass
class Connection:
    source:str
    target:str
    relation:str
    dashed:bool=False

@dataclass
class BackgroundSettings:
    source:str=""
    mode:str="tile"

@dataclass
class FamilyTreeData:
    persons:dict[str,Person]=field(default_factory=dict)
    connections:list[Connection]=field(default_factory=list)
    families:dict[str,Family]=field(default_factory=dict)
    background:BackgroundSettings=field(default_factory=BackgroundSettings)
    def add_person(self,p):self.persons[p.id]=p;self.ensure_families_for_person(p)
    def remove_person(self,pid):
        self.persons.pop(pid,None);self.connections=[c for c in self.connections if c.source!=pid and c.target!=pid]
    def ensure_family(self,name):
        name=name.strip()
        if not name:return None
        return self.families.setdefault(name,Family(name))
    def extract_family_names(self,family_name):
        return [x.strip() for x in family_name.strip().split("-") if x.strip()] if family_name.strip() else []
    def ensure_families_for_person(self,p):
        for n in self.extract_family_names(p.family_name):self.ensure_family(n)
    def get_family_colors(self,family_name):
        colors=[self.families[n].color for n in self.extract_family_names(family_name) if n in self.families]
        return colors or ["#ffffff"]
    def rename_family(self,old,new):
        old,new=old.strip(),new.strip()
        if not old or not new or old not in self.families:return
        if old==new:return
        f=self.families.pop(old);f.name=new;self.families[new]=f
        for p in self.persons.values():
            names=self.extract_family_names(p.family_name)
            if old in names:p.family_name="-".join(new if n==old else n for n in names)
    def remove_family(self,name):self.families.pop(name,None)
    def connect(self,source,target,relation):
        if source==target:return
        if any(c.source==source and c.target==target and c.relation==relation for c in self.connections):return
        self.connections.append(Connection(source,target,relation,relation=="spouse"))
    def disconnect(self,source,target,relation=None):
        self.connections=[c for c in self.connections if not(c.source==source and c.target==target and (relation is None or c.relation==relation))]
    def get_connections_for(self,pid):return[c for c in self.connections if c.source==pid or c.target==pid]
    def save(self,path):
        payload={"persons":{k:vars(v) for k,v in self.persons.items()},"connections":[vars(c) for c in self.connections],"families":{k:vars(v) for k,v in self.families.items()},"background":vars(self.background)}
        Path(path).write_text(json.dumps(payload,ensure_ascii=False,indent=2),encoding="utf-8")
    @classmethod
    def load(cls,path):
        raw=json.loads(Path(path).read_text(encoding="utf-8"));data=cls()
        for pid,p in raw.get("persons",{}).items():
            p=dict(p);p.setdefault("name_prefix","")
            data.persons[pid]=Person(id=pid,**{k:v for k,v in p.items() if k not in ("id","house_colors")})
        for name,f in raw.get("families",{}).items():data.families[name]=Family(name,f.get("color","#ffffff"))
        for p in data.persons.values():data.ensure_families_for_person(p)
        for c in raw.get("connections",[]):data.connections.append(Connection(**c))
        b=raw.get("background",{});data.background=BackgroundSettings(b.get("source",""),b.get("mode","tile"))
        return data
