from __future__ import annotations
from html import escape
from pathlib import Path
import base64,mimetypes
from models import FamilyTreeData,Person
from connections import orthogonal_path,spouse_path,CONNECTION_WIDTH
BOX_W,BOX_H,MAX_BOX_W=220,110,330
def box_width(data,p):
    longest=max(len(p.first_name or ""),len(p.name_prefix or ""),len(p.family_name or ""),1)
    return min(MAX_BOX_W,max(BOX_W,longest*9+30))
def font_size(data,p):
    width=box_width(data,p); longest=max(len(p.display_name()),1); available=width-20; estimated=longest*16*.58
    return 16 if estimated<=available else max(8,int(16*available/estimated))
def person_background(data,p):
    width=box_width(data,p);colors=data.get_family_colors(p.family_name)
    if len(colors)==1:return f'<rect x="{p.x}" y="{p.y}" width="{width}" height="{BOX_H}" fill="{escape(colors[0])}" rx="8"/>'
    stripe=width/len(colors);out=[]
    for i,c in enumerate(colors):out.append(f'<rect x="{p.x+i*stripe:.2f}" y="{p.y}" width="{stripe+.5:.2f}" height="{BOX_H}" fill="{escape(c)}"/>')
    out.append(f'<rect x="{p.x}" y="{p.y}" width="{width}" height="{BOX_H}" fill="none" stroke="#222" stroke-width="2" rx="8"/>')
    return "".join(out)
def background_svg(data):
    source=data.background.source
    if not source:return ""
    if source.startswith(("http://","https://")):
        if data.background.mode=="stretch":return f'<image href="{escape(source)}" x="0" y="0" width="100%" height="100%" preserveAspectRatio="none"/>'
        return f'<defs><pattern id="backgroundPattern" patternUnits="userSpaceOnUse" width="500" height="500"><image href="{escape(source)}" x="0" y="0" width="500" height="500" preserveAspectRatio="xMidYMid slice"/></pattern></defs><rect x="0" y="0" width="100%" height="100%" fill="url(#backgroundPattern)"/>'
    path=Path(source)
    if not path.is_file():return ""
    try:
        mime=mimetypes.guess_type(str(path))[0] or "image/png";uri=f"data:{mime};base64,{base64.b64encode(path.read_bytes()).decode('ascii')}"
        if data.background.mode=="stretch":return f'<image href="{uri}" x="0" y="0" width="100%" height="100%" preserveAspectRatio="none"/>'
        return f'<defs><pattern id="backgroundPattern" patternUnits="userSpaceOnUse" width="500" height="500"><image href="{uri}" x="0" y="0" width="500" height="500" preserveAspectRatio="xMidYMid slice"/></pattern></defs><rect x="0" y="0" width="100%" height="100%" fill="url(#backgroundPattern)"/>'
    except OSError:return ""
def export_svg(data,path):
    width=max(1200,(max((p.x+box_width(data,p) for p in data.persons.values()),default=1100)+100))
    height=max(800,(max((p.y+BOX_H for p in data.persons.values()),default=700)+100))
    parts=[f'<svg xmlns="http://www.w3.org/2000/svg" width="{width}" height="{height}" viewBox="0 0 {width} {height}">',background_svg(data),'<g id="connections" fill="none" stroke="#333">']
    for c in data.connections:
        a,b=data.persons.get(c.source),data.persons.get(c.target)
        if not a or not b:continue
        d=spouse_path(a,b,box_width(data,a),BOX_H) if c.relation=="spouse" else orthogonal_path(a,b,box_width(data,a),BOX_H)
        dash=' stroke-dasharray="10 7"' if c.dashed else ""
        width_attr=CONNECTION_WIDTH*1.35 if c.relation!="spouse" else CONNECTION_WIDTH
        parts.append(f'<path d="{d}" stroke-width="{width_attr}"{dash}/>')
    parts.append("</g><g id="persons" font-family="Arial, sans-serif">")
    for p in data.persons.values():
        w=box_width(data,p);s=font_size(data,p);parts.append(person_background(data,p))
        family=" ".join(x for x in (p.name_prefix,p.family_name) if x)
        parts += [f'<text x="{p.x+10}" y="{p.y+27}" font-size="{s}" font-weight="bold">{escape(p.first_name)}</text>',f'<text x="{p.x+10}" y="{p.y+49}" font-size="{s}">{escape(family)}</text>']
        if p.birth_date or p.death_date:
            from calendar_system import get_calendar
            def fmt(v):
                if isinstance(v,dict):
                    c=get_calendar(v.get("calendar_id",""));return c.format_date(v["day"],v["month"],v["year"]) if c else f'{v["day"]}.{v["month"]}.{v["year"]}'
                return str(v) if v else "—"
            parts += [f'<text x="{p.x+10}" y="{p.y+74}" font-size="11">Geb.: {escape(fmt(p.birth_date))}</text>',f'<text x="{p.x+10}" y="{p.y+94}" font-size="11">Tod: {escape(fmt(p.death_date))}</text>']
        if p.link:parts.append(f'<a href="{escape(p.link)}"><text x="{p.x+w-24}" y="{p.y+21}" font-size="17">🌐</text></a>')
    parts.append("</g></svg>");Path(path).write_text("\n".join(parts),encoding="utf-8")
