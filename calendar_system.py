from __future__ import annotations

from dataclasses import dataclass, asdict
from pathlib import Path
import json
import re

@dataclass
class CalendarDefinition:
    id: str
    name: str
    months: list[dict]
    era_name: str = "Anno Domini"
    era_abbreviation: str = "AD"

    @classmethod
    def load(cls, path: Path) -> "CalendarDefinition":
        raw=json.loads(path.read_text(encoding="utf-8"))
        return cls(raw.get("id",path.stem),raw.get("name",path.stem),raw.get("months",[]),raw.get("era_name","Era"),raw.get("era_abbreviation",""))

    def save(self,path:Path)->None:
        path.parent.mkdir(parents=True,exist_ok=True)
        path.write_text(json.dumps(asdict(self),ensure_ascii=False,indent=2),encoding="utf-8")

    def month_names(self)->list[str]:
        return [m.get("name","") for m in self.months]

    def month_days(self,month:int)->int:
        return int(self.months[month-1].get("days",0)) if 1<=month<=len(self.months) else 0

    def format_date(self,day:int|None,month:int|None,year:int)->str:
        parts=[]
        if day is not None and month is not None:
            name=self.months[month-1].get("name",str(month)) if 1<=month<=len(self.months) else str(month)
            parts.append(f"{day}. {name}")
        elif month is not None:
            name=self.months[month-1].get("name",str(month)) if 1<=month<=len(self.months) else str(month)
            parts.append(name)
        parts.append(str(year))
        if self.era_abbreviation:
            parts.append(self.era_abbreviation)
        return " ".join(parts)

    def parse_date(self,value:str)->tuple[int|None,int|None,int]|None:
        value=value.strip()
        if not value:return None
        parts=value.split()
        era_tokens={self.era_abbreviation.lower(),self.era_name.lower()}
        if parts and parts[-1].rstrip(".").lower() in era_tokens:
            parts=parts[:-1]
        # Year only.
        if len(parts)==1:
            try:return None,None,int(parts[0])
            except ValueError:return None
        # Month + year.
        if len(parts)==2:
            try:year=int(parts[1])
            except ValueError:year=None
            if year is not None:
                month_text=parts[0].rstrip(".")
                try:month=int(month_text)
                except ValueError:
                    month=next((i for i,m in enumerate(self.months,1) if month_text.lower()==str(m.get("name","")).lower()),0)
                if 1<=month<=len(self.months):
                    return None,month,year
        if len(parts)>=3:
            era_token=parts[-1].rstrip(".")
            body=parts[:-1] if era_token.lower() in {self.era_abbreviation.lower(),self.era_name.lower()} else parts
            if len(body)>=3:
                try:
                    day=int(body[0].rstrip("."))
                    year=int(body[-1])
                except ValueError:
                    day=year=None
                if day is not None:
                    month_text=" ".join(body[1:-1]).strip().rstrip(".")
                    for i,m in enumerate(self.months,1):
                        if month_text.lower() in {str(m.get("name","")).lower(),str(i)} and 1<=day<=self.month_days(i):
                            return day,i,year
        m=re.match(r"^(\d{1,3})[./-](\d{1,2})[./-](-?\d+)(?:\s+[^\s]+)?$",value)
        if m:
            day,month,year=map(int,m.groups())
            if 1<=month<=len(self.months) and 1<=day<=self.month_days(month):
                return day,month,year
        return None

def calendar_directory()->Path:
    return Path(__file__).resolve().parent/"calendars"

def load_calendars()->dict[str,CalendarDefinition]:
    result={}
    directory=calendar_directory(); directory.mkdir(parents=True,exist_ok=True)
    for path in sorted(directory.glob("*.json")):
        try:
            c=CalendarDefinition.load(path); result[c.id]=c
        except (OSError,ValueError,TypeError,json.JSONDecodeError):
            pass
    return result

def get_calendar(calendar_id:str)->CalendarDefinition|None:
    return load_calendars().get(calendar_id)
