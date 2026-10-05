from __future__ import annotations
import os, tkinter as tk, webbrowser
from tkinter import ttk, messagebox, filedialog
from urllib.request import urlopen
from models import FamilyTreeData, Person
from connections import CONNECTION_WIDTH
from dialogs import PersonDialog, FamilyDialog, BackgroundDialog, CalendarManagerDialog

BOX_W, BOX_H, MAX_BOX_WIDTH = 220, 110, 330
BASE_FONT, MIN_FONT = 16, 8

class TreeCanvas(tk.Canvas):
    def __init__(self,master,data,on_edit,**kwargs):
        super().__init__(master,background="#000000",highlightthickness=0,**kwargs)
        self.data,self.on_edit=data,on_edit
        self.zoom=1.0; self.pan_x=0.0; self.pan_y=0.0
        self.drag_id=None; self.drag_offset=(0,0); self.pan_start=None
        self.background_photo=None
        self.text_photos=[]
        self.bind("<ButtonPress-1>",self._press); self.bind("<B1-Motion>",self._drag); self.bind("<ButtonRelease-1>",self._release)
        self.bind("<ButtonPress-2>",self._middle_press); self.bind("<B2-Motion>",self._middle_drag); self.bind("<ButtonRelease-2>",self._middle_release)
        self.bind("<Button-3>",self._right_click); self.bind("<Double-Button-1>",self._double_click)
        self.bind("<MouseWheel>",self._wheel); self.bind("<Button-4>",lambda e:self._zoom_at(e.x,e.y,1.1)); self.bind("<Button-5>",lambda e:self._zoom_at(e.x,e.y,.9))
        self.bind("<Configure>",lambda e:self.redraw()); self.redraw()

    def world_to_screen(self,x,y): return x*self.zoom+self.pan_x,y*self.zoom+self.pan_y
    def screen_to_world(self,x,y): return (x-self.pan_x)/self.zoom,(y-self.pan_y)/self.zoom
    def redraw(self):
        self.delete("all"); self.text_photos=[]; self._draw_background(); self._draw_connections(); self._draw_persons()
    def _load_background_image(self,source):
        from PIL import Image
        from io import BytesIO
        if source.startswith(("http://","https://")):
            req=__import__("urllib.request",fromlist=["Request"]).Request(source,headers={"User-Agent":"FantasyFamilyTree/1.0"})
            with urlopen(req,timeout=10) as r: return Image.open(BytesIO(r.read())).convert("RGB")
        if os.path.isfile(source): return Image.open(source).convert("RGB")
        return None
    def _draw_background(self):
        source=self.data.background.source
        if not source:return
        try:
            from PIL import Image,ImageTk
            image=self._load_background_image(source)
            if image is None:return
            from PIL import Image
            alpha=max(0.0,min(1.0,float(self.data.background.alpha)))
            image=Image.blend(Image.new("RGB",image.size,(0,0,0)),image,alpha)
            w=max(1,self.winfo_width()); h=max(1,self.winfo_height())
            if self.data.background.mode=="stretch":
                image=image.resize((w,h))
                self.background_photo=ImageTk.PhotoImage(image)
                self.create_image(0,0,anchor="nw",image=self.background_photo,tags="background")
            else:
                result=Image.new("RGB",(w,h))
                for x in range(0,w,image.width):
                    for y in range(0,h,image.height): result.paste(image,(x,y))
                self.background_photo=ImageTk.PhotoImage(result)
                self.create_image(0,0,anchor="nw",image=self.background_photo,tags="background")
            self.tag_lower("background")
        except Exception: pass

    def _box_width(self,p):
        # Size the box for the actual two name lines.
        line1=p.first_name or ""
        line2=" ".join(q for q in (p.name_prefix,p.family_name) if q)
        longest=max(len(line1),len(line2),1)
        return max(BOX_W,longest*10+34)

    def _fit_text(self,text,font,available_width):
        # Canvas text does not clip to a rectangle, so shorten names explicitly.
        if not text:return ""
        from tkinter import font as tkfont
        f=tkfont.Font(font=font)
        if f.measure(text)<=available_width:return text
        ellipsis="..."
        if f.measure(ellipsis)>available_width:return ""
        lo,hi=0,len(text)
        while lo<hi:
            mid=(lo+hi+1)//2
            if f.measure(text[:mid]+ellipsis)<=available_width:lo=mid
            else:hi=mid-1
        return text[:lo]+ellipsis

    def _font_size(self,p):
        w=self._box_width(p)
        longest=max(len(p.first_name or ""),len(" ".join(q for q in (p.name_prefix,p.family_name) if q)),1)
        return max(MIN_FONT,min(BASE_FONT,int((w-20)/(max(longest,1)*0.58))))

    def _contrast_text(self,colors):
        def rgb(v):
            v=v.lstrip("#")
            if len(v)!=6:return (255,255,255)
            return tuple(int(v[i:i+2],16) for i in (0,2,4))
        vals=[rgb(c) for c in colors]
        def lum(v):
            q=[]
            for x in v:
                x/=255
                q.append(x/12.92 if x<=.04045 else ((x+.055)/1.055)**2.4)
            return .2126*q[0]+.7152*q[1]+.0722*q[2]
        def ratio(t,b):
            a,c=lum(t),lum(b);return (max(a,c)+.05)/(min(a,c)+.05)
        return "#000000" if min(ratio((0,0,0),v) for v in vals)>=min(ratio((255,255,255),v) for v in vals) else "#ffffff"

    def _contrast_text_at(self,colors,box_width,text_x,text_width):
        # Kept for callers that need one colour, but split boxes are rendered
        # character-by-character so the text colour can change at the family
        # colour boundary.
        if len(colors)<=1:
            return self._contrast_text(colors)
        stripe=box_width/len(colors)
        covered=[]
        left=text_x
        right=text_x+text_width
        for i,color in enumerate(colors):
            stripe_left=i*stripe
            stripe_right=(i+1)*stripe
            if right>stripe_left and left<stripe_right:
                covered.append(color)
        return self._contrast_text(covered or [colors[0]])

    def _font_file(self,bold=False):
        import os
        candidates=[]
        if os.name=="nt":
            candidates += [r"C:\\Windows\\Fonts\\arialbd.ttf" if bold else r"C:\\Windows\\Fonts\\arial.ttf"]
        candidates += [
            "/usr/share/fonts/truetype/msttcorefonts/Arial_Bold.ttf" if bold else "/usr/share/fonts/truetype/msttcorefonts/Arial.ttf",
            "/usr/share/fonts/truetype/liberation2/LiberationSans-Bold.ttf" if bold else "/usr/share/fonts/truetype/liberation2/LiberationSans-Regular.ttf",
            "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf" if bold else "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
        ]
        return next((p for p in candidates if os.path.isfile(p)),None)

    def _draw_text_split(self,text,x,y,font,colors,box_width,tag):
        if not text:
            return
        from tkinter import font as tkfont
        f=tkfont.Font(font=font)
        if len(colors)<=1:
            self.create_text(x,y,anchor="w",text=text,font=font,
                             fill=self._contrast_text(colors),tags=tag)
            return

        # Render the complete string into one RGBA image and clip its alpha
        # mask to the family-colour stripes. This allows a single glyph to be
        # split at the boundary instead of assigning one colour per character.
        try:
            from PIL import Image,ImageDraw,ImageFont,ImageChops,ImageTk
            bold=len(font)>=3 and font[2]=="bold"
            size=max(1,int(font[1]))
            font_path=self._font_file(bold)
            if not font_path:
                raise OSError("No compatible TrueType font found")
            pil_font=ImageFont.truetype(font_path,size)
            bbox=pil_font.getbbox(text)
            tw=max(1,bbox[2]-bbox[0]+4)
            th=max(1,bbox[3]-bbox[1]+4)
            base=Image.new("RGBA",(tw,th),(0,0,0,0))
            stripe_width=box_width/len(colors)
            for i,color in enumerate(colors):
                layer=Image.new("RGBA",(tw,th),(0,0,0,0))
                draw=ImageDraw.Draw(layer)
                draw.text((2-bbox[0],2-bbox[1]),text,font=pil_font,fill=self._contrast_text([color]))
                mask=Image.new("L",(tw,th),0)
                md=ImageDraw.Draw(mask)
                # Text image starts at the same x coordinate as the first
                # glyph, so stripe coordinates are relative to the person box.
                text_start_in_box=10*self.zoom
                left=i*stripe_width-text_start_in_box
                right=(i+1)*stripe_width-text_start_in_box
                md.rectangle((max(0,left),0,min(tw,right),th),fill=255)
                alpha=ImageChops.multiply(layer.getchannel("A"),mask)
                layer.putalpha(alpha)
                base=Image.alpha_composite(base,layer)
            photo=ImageTk.PhotoImage(base)
            self.text_photos.append(photo)
            self.create_image(x,y-th/2,anchor="nw",image=photo,tags=tag)
        except Exception:
            # Portable fallback for systems without a usable TrueType font.
            # The normal character rendering still preserves the split.
            stripe=box_width/len(colors)
            cursor=x
            for char in text:
                width=f.measure(char)
                midpoint=(cursor-x)+(width/2)
                index=min(len(colors)-1,max(0,int(midpoint/stripe)))
                self.create_text(cursor,y,anchor="w",text=char,font=font,
                                 fill=self._contrast_text([colors[index]]),tags=tag)
                cursor+=width

    def _striped_polyline(self,points,colors,dashed=False,widths=None,arrow=True):
        # Contrasting outline plus up to four parallel longitudinal colour
        # stripes. Only the outline carries the shared arrowhead.
        def screen(p): return self.world_to_screen(p[0],p[1])
        outer=max(2,int((CONNECTION_WIDTH+4)*self.zoom))
        sp=[screen(p) for p in points]
        flat=[v for p in sp for v in p]
        arrow_mode=tk.LAST if arrow else tk.NONE
        self.create_line(*flat,fill="#ffffff",width=outer+3,arrow=arrow_mode,tags="connection")
        self.create_line(*flat,fill="#000000",width=outer,arrow=arrow_mode,tags="connection")
        colors=colors[:4] or ["#ffffff"]
        n=len(colors)
        for j in range(len(sp)-1):
            scale=(widths[j] if widths and j<len(widths) else 1.0)
            segment_inner=max(1,CONNECTION_WIDTH*self.zoom*scale)
            segment_stripe=max(1,segment_inner/n)
            x1,y1=sp[j];x2,y2=sp[j+1]
            dx,dy=x2-x1,y2-y1; length=max((dx*dx+dy*dy)**0.5,1)
            nx,ny=-dy/length,dx/length
            for i,color in enumerate(colors):
                offset=(i-(n-1)/2)*segment_stripe
                ox,oy=nx*offset,ny*offset
                self.create_line(
                    x1+ox,y1+oy,x2+ox,y2+oy,
                    fill=color,width=max(1,int(segment_stripe)+1),
                    arrow=tk.NONE,tags="connection"
                )

    def _draw_connections(self):
        # Spouse connections are independent. Parent connections are grouped
        # by child so the final segment becomes one combined multicolor arrow.
        parent_groups={}
        for c in self.data.connections:
            a=self.data.persons.get(c.source)
            b=self.data.persons.get(c.target)
            if not a or not b: continue
            if c.relation=="parent":
                parent_groups.setdefault(c.target,[]).append(a)
            else:
                colors=self.data.get_family_colors(a.family_name)
                points=[
                    (a.x+self._box_width(a),a.y+BOX_H/2),
                    ((a.x+self._box_width(a)+b.x)/2,a.y+BOX_H/2),
                    ((a.x+self._box_width(a)+b.x)/2,b.y+BOX_H/2),
                    (b.x,b.y+BOX_H/2)
                ]
                self._striped_polyline(points,colors,True,[1.0,1.0,1.0])

        for child_id,parents in parent_groups.items():
            child=self.data.persons.get(child_id)
            if not child: continue
            parents=sorted(parents,key=lambda p:(p.y,p.x,p.id))
            child_cx=child.x+self._box_width(child)/2
            junction_y=child.y-(BOX_H*0.35)
            combined=[]
            for parent in parents:
                parent_colors=self.data.get_family_colors(parent.family_name)
                for color in parent_colors:
                    if color not in combined and len(combined)<4:
                        combined.append(color)
                branch=[
                    (parent.x+self._box_width(parent)/2,parent.y+BOX_H),
                    (parent.x+self._box_width(parent)/2,junction_y),
                    (child_cx,junction_y)
                ]
                self._striped_polyline(branch,parent_colors,False,[1.35,0.9],False)
            if not combined: combined=["#ffffff"]
            self._striped_polyline(
                [(child_cx,junction_y),(child_cx,child.y)],
                combined,False,[0.75],True
            )

    def _polyline(self,points,dashed=False,width=None,width2=None):
        flat=[]
        for x,y in points: flat.extend(self.world_to_screen(x,y))
        kwargs={"fill":"#333333","width":max(1,int((width or CONNECTION_WIDTH)*self.zoom))}
        if dashed: kwargs["dash"]=(max(2,int(10*self.zoom)),max(2,int(7*self.zoom)))
        self.create_line(*flat,**kwargs,tags="connection")
    def _draw_persons(self):
        for p in self.data.persons.values(): self._draw_person(p)
    def _draw_person(self,p):
        x,y=self.world_to_screen(p.x,p.y); w,h=self._box_width(p)*self.zoom,BOX_H*self.zoom
        colors=self.data.get_family_colors(p.family_name); tag=f"person:{p.id}"
        if len(colors)==1:
            self.create_rectangle(x,y,x+w,y+h,fill=colors[0],outline="#222",width=2,tags=tag)
        else:
            # Exactly two families are split 50/50.
            stripe=w/len(colors)
            for i,color in enumerate(colors): self.create_rectangle(x+i*stripe,y,x+(i+1)*stripe+1,y+h,fill=color,outline="",tags=tag)
            self.create_rectangle(x,y,x+w,y+h,fill="",outline="#222",width=2,tags=tag)
        if self.zoom>=0.42:
            fs=max(MIN_FONT,int(self._font_size(p)*self.zoom))
            first_font=("Arial",fs,"bold")
            family_font=("Arial",fs)
            available=max(1,w-20*self.zoom)
            first=self._fit_text(p.first_name,first_font,available)
            family=" ".join(q for q in (p.name_prefix,p.family_name) if q)
            family=self._fit_text(family,family_font,available)
            box_width=self._box_width(p)*self.zoom
            self._draw_text_split(first,x+10*self.zoom,y+25*self.zoom,
                                  first_font,colors,box_width,tag)
            self._draw_text_split(family,x+10*self.zoom,y+48*self.zoom,
                                  family_font,colors,box_width,tag)
        if self.zoom>=0.62:
            date_font=("Arial",max(7,int(11*self.zoom)))
            birth=self._date_text(p.birth_date)
            death=self._date_text(p.death_date)
            box_width=self._box_width(p)*self.zoom
            self._draw_text_split(f"Geb.: {birth}",x+10*self.zoom,
                                  y+73*self.zoom,date_font,colors,box_width,tag)
            self._draw_text_split(f"Tod: {death}",x+10*self.zoom,
                                  y+92*self.zoom,date_font,colors,box_width,tag)
        if p.link and self.zoom>=0.35:self.create_text(x+w-17*self.zoom,y+17*self.zoom,text="🌐",font=("Arial",max(8,int(13*self.zoom))),tags=tag)
    def _date_text(self,v):
        if not v:return "—"
        if isinstance(v,dict):
            from calendar_system import get_calendar
            c=get_calendar(v.get("calendar_id",""))
            return c.format_date(v["day"],v["month"],v["year"]) if c else f'{v["day"]}.{v["month"]}.{v["year"]}'
        return str(v)

    def _person_at(self,e):
        wx,wy=self.screen_to_world(e.x,e.y)
        for p in reversed(list(self.data.persons.values())):
            if p.x<=wx<=p.x+self._box_width(p) and p.y<=wy<=p.y+BOX_H:return p
        return None
    def _press(self,e):
        p=self._person_at(e)
        if not p:self.drag_id=None; return
        self.drag_id=p.id; wx,wy=self.screen_to_world(e.x,e.y); self.drag_offset=(wx-p.x,wy-p.y)
    def _drag(self,e):
        if not self.drag_id:return
        p=self.data.persons[self.drag_id]; wx,wy=self.screen_to_world(e.x,e.y)
        p.x=wx-self.drag_offset[0]; p.y=wy-self.drag_offset[1]; self.redraw()
    def _release(self,e):self.drag_id=None
    def _middle_press(self,e):self.pan_start=(e.x,e.y,self.pan_x,self.pan_y)
    def _middle_drag(self,e):
        if self.pan_start:
            x,y,px,py=self.pan_start; self.pan_x=px+e.x-x; self.pan_y=py+e.y-y; self.redraw()
    def _middle_release(self,e):self.pan_start=None
    def _wheel(self,e):
        self._zoom_at(e.x,e.y,1.1 if e.delta>0 else .9)
    def _zoom_at(self,sx,sy,factor):
        old=self.zoom; new=max(.05,min(5.0,old*factor))
        if new==old:return
        wx,wy=self.screen_to_world(sx,sy); self.zoom=new
        self.pan_x=sx-wx*new; self.pan_y=sy-wy*new; self.redraw()
    def _right_click(self,e):
        p=self._person_at(e)
        if not p:return
        menu=tk.Menu(self,tearoff=False); menu.add_command(label="Editieren",command=lambda:self.on_edit(p))
        if p.link:menu.add_command(label="Link öffnen",command=lambda:webbrowser.open(p.link))
        menu.add_separator(); menu.add_command(label="Person löschen",command=lambda:self._delete_person(p))
        try:menu.tk_popup(e.x_root,e.y_root)
        finally:menu.grab_release()
    def _double_click(self,e):
        p=self._person_at(e)
        if p:self.on_edit(p)
    def _delete_person(self,p):
        if messagebox.askyesno("Person löschen",f"Soll {p.display_name()} wirklich gelöscht werden?"):
            self.data.remove_person(p.id); self.redraw()

    def auto_layout(self):
        persons=self.data.persons
        if not persons:return

        # Build the parent/child graph first.  The generation with the most
        # people is used as the fixed reference row; all other rows are then
        # positioned relative to people that are already positioned.
        parents={pid:[] for pid in persons}
        children={pid:[] for pid in persons}
        for c in self.data.connections:
            if c.relation=="parent" and c.source in persons and c.target in persons:
                parents[c.target].append(c.source)
                children[c.source].append(c.target)

        generations={}
        def gen(pid,stack=None):
            if pid in generations:return generations[pid]
            stack=set() if stack is None else set(stack)
            if pid in stack:return 0
            stack.add(pid)
            value=max((gen(parent,stack)+1 for parent in parents[pid]),default=0)
            generations[pid]=value
            return value

        for pid in persons:
            gen(pid)

        rows={}
        for pid,g in generations.items():
            rows.setdefault(g,[]).append(pid)

        # Pick the densest generation as the visual anchor.  Existing x
        # positions are only used to make repeated auto-layouts stable.
        anchor_g=max(rows,key=lambda g:(len(rows[g]),-g))
        anchor=rows[anchor_g]
        anchor.sort(key=lambda pid:(persons[pid].x,persons[pid].y,pid))

        # A slot is a logical horizontal unit.  It is deliberately wider
        # than the smallest person box so the reference row never overlaps.
        slot=max(self._box_width(persons[pid]) for pid in anchor)+4
        anchor_centers={}
        for i,pid in enumerate(anchor):
            center=i*slot
            p=persons[pid]
            p.x=center-self._box_width(p)/2
            p.y=80+anchor_g*(BOX_H+80)
            anchor_centers[pid]=center

        positioned=set(anchor)

        def center(pid):
            p=persons[pid]
            return p.x+self._box_width(p)/2

        def related_target(pid,other_generation):
            refs=[]
            if other_generation < generations[pid]:
                refs=[x for x in parents[pid] if x in positioned]
            else:
                refs=[x for x in children[pid] if x in positioned]
            if refs:
                return sum(center(x) for x in refs)/len(refs)
            return None

        def place_row(g,reference_direction):
            row=rows.get(g,[])
            if not row:return
            # Put each person near the barycentre of their already-positioned
            # relatives.  This keeps branches under/over their actual family
            # instead of rebuilding every row from x=80.
            targets=[]
            fallback=sum(center(pid) for pid in positioned)/len(positioned) if positioned else 0
            for pid in row:
                target=related_target(pid,reference_direction)
                targets.append((fallback if target is None else target,pid))
            targets.sort(key=lambda item:(item[0],persons[item[1]].display_name().lower(),item[1]))

            y=80+g*(BOX_H+80)
            previous_right=None
            for target,pid in targets:
                p=persons[pid]
                w=self._box_width(p)
                x=target-w/2
                if previous_right is not None and x<previous_right+4:
                    x=previous_right+4
                p.x=x
                p.y=y
                previous_right=x+w
                positioned.add(pid)

            # A row can be pushed right by collision resolution.  Recenter the
            # whole row around its relationship targets without ever creating
            # an overlap.  The anchor row remains untouched.
            if row is not anchor and len(targets)>1:
                desired=sum(t for t,_ in targets)/len(targets)
                actual=sum(center(pid) for _,pid in targets)/len(targets)
                shift=desired-actual
                if shift:
                    for _,pid in targets:
                        persons[pid].x+=shift

                # The shift above can only preserve internal gaps; clamp the
                # first box against its nearest previous box when necessary.
                ordered=sorted((persons[pid] for _,pid in targets),key=lambda p:p.x)
                for i,p in enumerate(ordered):
                    if i:
                        minimum=ordered[i-1].x+self._box_width(ordered[i-1])+4
                        if p.x<minimum:p.x=minimum

        # Work outwards from the densest row.  For parents, children are the
        # reference points; for children, parents are the reference points.
        for g in range(anchor_g-1,-1,-1):
            place_row(g,g+1)
        positioned=set(anchor)
        for g in range(anchor_g+1,max(rows,default=anchor_g)+1):
            place_row(g,g-1)

        self.redraw()

class SidePanel(ttk.Frame):
    def __init__(self,master,data,refresh,**kwargs):
        super().__init__(master,padding=8,**kwargs); self.data=data; self.refresh=refresh
        ttk.Label(self,text="Stammbaum",font=("Arial",15,"bold")).pack(anchor="w")
        ttk.Button(self,text="+ Person hinzufügen",command=self.add_person).pack(fill="x",pady=(8,10))
        ttk.Button(self,text="Kalender verwalten",command=self.manage_calendars).pack(fill="x",pady=2)
        ttk.Button(self,text="Automatisch anordnen",command=self.auto_layout).pack(fill="x",pady=2)
        ttk.Button(self,text="Hintergrund",command=self.background).pack(fill="x",pady=2)
        ttk.Label(self,text="Personen",font=("Arial",11,"bold")).pack(anchor="w",pady=(10,0))
        self.listbox=tk.Listbox(self,height=12); self.listbox.pack(fill="both",expand=True); self.listbox.bind("<Double-Button-1>",self.edit_selected)
        ttk.Label(self,text="Familien",font=("Arial",11,"bold")).pack(anchor="w",pady=(10,0))
        self.family_list=tk.Listbox(self,height=6); self.family_list.pack(fill="x"); self.family_list.bind("<Double-Button-1>",self.edit_family)
        self.update_list()
    def update_list(self):
        self.listbox.delete(0,"end")
        for p in self.data.persons.values():self.listbox.insert("end",p.display_name())
        self.family_list.delete(0,"end")
        for f in self.data.families.values():self.family_list.insert("end",f.name)
    def add_person(self):
        import uuid
        p=Person(id=str(uuid.uuid4()),first_name="Neue",family_name="Person"); self.data.add_person(p); self.refresh()
        # app callback opens editor only for explicit canvas/add button in old code; open via list is enough.
    def edit_selected(self,e=None):
        if self.listbox.curselection():
            p=list(self.data.persons.values())[self.listbox.curselection()[0]]
            self.master.master.open_editor(p)
    def edit_family(self,e=None):
        if self.family_list.curselection():
            f=list(self.data.families.values())[self.family_list.curselection()[0]]; FamilyDialog(self,self.data,f,self.refresh)
    def manage_calendars(self):CalendarManagerDialog(self,self.refresh)
    def background(self):BackgroundDialog(self,self.data,self.refresh)
    def auto_layout(self):
        if getattr(self,"canvas",None) is not None:
            self.canvas.auto_layout()
            self.refresh()

