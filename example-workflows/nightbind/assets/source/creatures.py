"""Thirteen original reliquary creatures, individually authored silhouettes."""
import math
from meshkit import Mesh,root,socket

def ember():
    r=root('ember'); b=Mesh()
    b.ellipsoid((0,0,.62),(.46,.39,.56),'night',8,3)
    for s in (-1,1):
        b.box((s*.23,-.10,.10),(.22,.35,.20),'slate')
        b.prism([(s*.04,.66),(s*.43,.76),(s*.32,1.17),(s*.22,1.35),(s*.18,.97)],-.15,.12,'ember')
    b.cup((0,-.27,.63),.30,.20,'ember',8,1,.08,axis='y')
    b.prism([(-.07,.44),(.02,.39),(.12,.65),(.04,.82),(-.01,.61)],-.485,-.465,'glow',glow=True)
    b.object('body',r); socket(r,'socket_attack',(0,-.49,.65)); return r

def thorn():
    r=root('thorn'); b=Mesh()
    b.prism([(-.45,-.48),(-.70,-.13),(-.60,.43),(0,.62),(.60,.43),(.70,-.13),(.45,-.48)],.30,.82,'thorn',axis='z')
    b.prism([(-.56,-.12),(0,-.40),(.56,-.12),(.40,.42),(0,.55),(-.40,.42)],.82,.91,'teal',axis='z')
    for x,y,h in [(-.36,.16,1.13),(0,.30,1.25),(.36,.12,1.08)]:
        b.prism([(x-.14,.84),(x-.105,h),(x+.07,h),(x+.15,.84)],y-.10,y+.10,'bone')
    for x in (-.43,.43):
        for y in (-.33,.36): b.box((x,y,.17),(.26,.25,.34),'dark')
    b.box((0,-.54,.43),(.59,.28,.38),'thorn',.065)
    b.box((0,-.695,.44),(.43,.04,.12),'night'); b.object('body',r)
    socket(r,'socket_attack',(0,-.73,.46)); return r

def volt():
    r=root('volt'); b=Mesh()
    b.ellipsoid((0,-.10,.55),(.15,.43,.22),'dark',6,2)
    b.prism([(-.06,.22),(-.26,.59),(0,.44),(.26,.59),(.06,.22)],.49,.57,'volt',axis='z')
    b.prism([(-.10,.45),(0,.08),(.10,.45)],-.54,-.34,'volt')
    b.object('body',r)
    for s,name in [(-1,'wing_l'),(1,'wing_r')]:
        w=Mesh(); pts=[(s*.09,-.25),(s*.72,-.46),(s*.90,-.20),(s*.76,-.25),(s*.57,.08),(s*.32,.15),(s*.10,.04)]
        w.prism(pts,.67,.78,'volt',axis='z')
        w.prism([(s*.18,-.22),(s*.71,-.37),(s*.59,-.10),(s*.38,.02)],.782,.794,'teal',axis='z')
        w.object(name,r,(s*.10,-.08,.72))
    socket(r,'socket_attack',(0,-.55,.55)); return r

def mire():
    r=root('mire'); b=Mesh()
    b.prism([(-.56,-.57),(-.67,-.06),(-.46,.58),(.12,.67),(.57,.45),(.63,.10),(.35,.24),(-.06,.25),(-.23,-.19),(.12,-.50)],.04,.29,'teal',axis='z')
    b.ellipsoid((.03,.12,.45),(.49,.42,.34),'mire',7,2)
    b.cup((-.12,-.02,.46),.30,.64,'mire',7,1.08,.09)
    b.cup((.40,.16,.48),.18,.44,'mire',6,1.1,.065)
    b.cup((-.34,.33,.38),.16,.29,'mire',6,1.14,.06)
    b.object('body',r); socket(r,'socket_attack',(-.12,-.02,1.11)); return r

def fang():
    r=root('fang'); b=Mesh()
    b.ellipsoid((0,.07,.64),(.28,.51,.27),'dark',7,2)
    b.ellipsoid((0,-.23,.77),(.32,.26,.30),'fang',6,2)
    for s in (-1,1):
        for y,top in [(-.30,.75),(.42,.59)]:
            b.tube([(s*.22,y,top),(s*.32,y+.12,.27),(s*.30,y-.09,.06)],[.105,.07,.09],'fang',5)
    b.tube([(0,.41,.66),(0,.75,.76),(0,.86,.97)],[.075,.06,.01],'fang',5)
    b.object('body',r)
    h=Mesh(); h.prism([(-.23,.92),(-.18,1.14),(0,1.23),(.18,1.14),(.23,.92),(.12,.75),(-.12,.75)],-.39,-.18,'fang')
    h.prism([(-.18,-.29),(-.12,-.83),(.12,-.83),(.18,-.29)],.82,1.00,'fang',axis='z')
    for s in (-1,1):
        h.prism([(s*.11,1.03),(s*.24,1.37),(s*.29,1.06)],-.29,-.13,'dark')
    h.box((0,-.84,.88),(.23,.09,.16),'night'); h.object('head',r,(0,-.20,.87))
    j=Mesh(); j.box((0,-.56,.77),(.23,.48,.11),'dark')
    for s in (-1,1): j.tube([(s*.14,-.68,.76),(s*.15,-.74,.99),(s*.12,-.79,1.03)],[.05,.028,.006],'bone',5)
    j.object('jaw',r,(0,-.34,.78)); socket(r,'socket_attack',(0,-.92,.89)); return r

def moth():
    r=root('moth'); b=Mesh(); b.ellipsoid((0,0,.69),(.12,.37,.17),'night',6,2)
    b.ellipsoid((0,-.28,.78),(.14,.13,.12),'moth',6,2); b.object('body',r)
    for s,name in [(-1,'wing_l'),(1,'wing_r')]:
        w=Mesh()
        for cx,cy,rx,ry in [(s*.45,-.26,.40,.32),(s*.37,.25,.31,.27)]:
            pts=[(cx+rx*math.cos(j*math.tau/8),cy+ry*math.sin(j*math.tau/8)) for j in range(8)]
            w.prism(pts,.70,.79,'moth',axis='z')
        w.prism([(s*.09,-.15),(s*.36,-.06),(s*.16,.20)],.794,.806,'dark',axis='z')
        w.prism([(s*.29,.34),(s*.49,.54),(s*.43,.71),(s*.21,.45)],.62,.71,'moth',axis='z')
        w.object(name,r,(s*.10,0,.75))
    socket(r,'socket_attack',(0,-.41,.79)); return r

def pyre():
    r=root('pyre'); b=Mesh()
    for s in (-1,1):
        b.box((s*.47,0,.19),(.49,.67,.38),'dark',.07)
        b.prism([(s*.24,.34),(s*.65,.38),(s*.65,1.58),(s*.38,1.88),(s*.25,1.56)],-.36,.36,'thorn')
        b.prism([(s*.56,1.09),(s*1.05,1.22),(s*.98,1.79),(s*.63,1.94),(s*.45,1.65)],-.30,.38,'teal')
    # Furnace walls form a genuine opening across the torso, framed by a hot lip.
    b.box((0,0,.59),(.91,.72,.24),'brass',.06); b.box((0,.17,1.79),(1.1,.72,.25),'thorn',.06)
    for x,h in [(-.37,2.13),(0,2.35),(.37,2.22)]: b.cup((x,.13,1.85),.14,h-1.85,'ember',6,1,.04)
    b.tube([(-.29,-.40,.78),(-.31,-.40,1.48),(0,-.40,1.66),(.31,-.40,1.48),(.29,-.40,.78)],.055,'ember',5)
    b.ellipsoid((0,.03,.93),(.17,.16,.28),'glow',7,2,True); b.object('body',r)
    socket(r,'socket_attack',(0,-.43,1.17)); socket(r,'socket_core',(0,0,1.15)); return r

def storm():
    r=root('storm'); b=Mesh()
    pts=[(-1.18,-.63,.28),(-.46,-.78,.35),(.55,-.60,.40),(.91,-.18,.48),(.35,.13,.55),(-.51,.20,.64),(-.84,.51,.74),(-.38,.81,.87)]
    b.tube(pts,[.10,.17,.23,.25,.24,.23,.21,.27],'volt',7)
    for p in [pts[2],pts[4],pts[5]]: b.cup((p[0],p[1],p[2]+.05),.17,.20,'mire',6,1,.05)
    b.prism([(-1.08,-.63),(-1.40,-.91),(-1.34,-.40),(-.93,-.48)],.24,.33,'volt',axis='z')
    b.object('body',r)
    h=Mesh(); h.prism([(-.60,.87),(-.61,.40),(-.33,.27),(.05,.39),(-.09,.87)],.80,1.09,'teal',axis='z')
    for s in (-1,1):
        h.prism([(-.31+s*.10,.96),(-.31+s*.63,1.38),(-.31+s*.47,.99),(-.31+s*.18,.84)],.73,.91,'volt')
    h.object('head',r,(-.32,.78,.96)); socket(r,'socket_attack',(-.31,.24,.99)); return r

def dusk():
    r=root('dusk'); b=Mesh()
    b.tube([(0,.16,.32),(0,.13,1.02),(0,-.22,1.61)],[.27,.36,.30],'fang',7)
    for s in (-1,1):
        b.tube([(s*.25,.15,.62),(s*.42,.29,.28),(s*.39,-.07,.04)],[.14,.10,.15],'dark',5)
    b.tube([(0,.30,.59),(.39,.69,.83),(.56,.79,1.32),(.43,.71,1.57),(.24,.57,1.46)],[.13,.12,.08,.06,.005],'fang',6)
    b.prism([(-.17,-.28),(-.14,-.90),(.14,-.90),(.23,-.30)],1.46,1.75,'fang',axis='z')
    for s in (-1,1):
        b.prism([(s*.12,1.64),(s*.26,2.14),(s*.30,1.62)],-.26,-.08,'dark')
        b.tube([(s*.17,-.67,1.43),(s*.17,-.73,1.74)],[.06,.006],'bone',5)
    b.object('body',r)
    for s,name in [(-1,'wing_l'),(1,'wing_r')]:
        w=Mesh(); w.prism([(s*.22,1.48),(s*.70,2.34),(s*1.16,2.02),(s*1.08,1.51),(s*.77,1.17),(s*.67,1.61),(s*.43,.94),(s*.28,1.16)],-.02,.23,'moth')
        w.prism([(s*.34,1.54),(s*.70,2.16),(s*.91,1.99),(s*.60,1.68)],-.065,-.025,'dark')
        w.object(name,r,(s*.21,0,1.48))
    socket(r,'socket_attack',(0,-.97,1.61)); return r

def solar():
    r=root('solar'); b=Mesh()
    # Near-horizontal sunwheel preserves its aperture through all four game facings.
    points=[(.59*math.cos(j*math.tau/12),.64*math.sin(j*math.tau/12),1.51+.10*math.sin(j*math.tau/12)) for j in range(13)]
    b.tube(points,.105,'brass',7)
    b.ellipsoid((0,.03,1.51),(.19,.15,.25),'ember',8,3,True)
    for j in range(6):
        a=j*math.tau/6; ux,uz=math.cos(a),math.sin(a); tx,tz=-uz,ux
        outline=[(ux*.54+tx*.08,uz*.54+tz*.08),(ux*1.35+tx*.26,uz*1.16+tz*.26),(ux*1.60+tx*.07,uz*1.35+tz*.07),(ux*1.54-tx*.13,uz*1.28-tz*.13),(ux*.83-tx*.22,uz*.66-tz*.22)]
        b.prism(outline,1.47,1.54,'ivory' if j%2 else 'volt',axis='z')
    b.object('body',r)
    for s,name in [(-1,'wing_l'),(1,'wing_r')]:
        v=Mesh(); v.prism([(s*.38,1.18),(s*.59,.77),(s*.39,.07),(s*.14,.43),(s*.20,.96)],-.03,.045,'moth')
        v.object(name,r,(s*.30,0,1.15))
    socket(r,'socket_attack',(0,-.33,1.51)); socket(r,'socket_core',(0,0,1.51)); return r

def world():
    r=root('world'); b=Mesh()
    # An open ring in three dimensions, with a lower front jaw occupying its gap.
    pts=[]
    for j in range(15):
        a=math.radians(-58+j*302/14); pts.append((1.13*math.cos(a),.95*math.sin(a),1.05+.15*math.sin(a)))
    b.tube(pts,[.22+.04*math.sin(j*.7) for j in range(15)],'volt',8)
    for j in (2,5,8,11):
        p=pts[j]; b.tube([(p[0],p[1],p[2]+.10),(p[0]*1.10,p[1],p[2]+.33)],[.14,.03],'thorn',6)
    b.object('body',r)
    h=Mesh(); h.prism([(.22,-.44),(.16,-1.18),(.62,-1.32),(1.0,-.91),(.85,-.39)],.55,1.08,'thorn',axis='z')
    for x,hz in [(.29,1.41),(.52,1.56),(.76,1.36)]: h.prism([(x-.11,.99),(x-.07,hz),(x+.04,hz+.03),(x+.11,.99)],-.78,-.52,'bone')
    h.object('head',r,(.55,-.47,.79))
    j=Mesh(); j.box((.53,-.88,.48),(.58,.64,.17),'dark',.06)
    for x in (.26,.78): j.tube([(x,-1.01,.54),(x,-1.14,.86)],[.08,.012],'bone',6)
    j.object('jaw',r,(.54,-.60,.54)); socket(r,'socket_attack',(.56,-1.32,.80)); socket(r,'socket_core',(0,0,1.17)); return r

def eclipse():
    r=root('eclipse'); b=Mesh()
    # Crescent back sweeps around an open moon, then narrows into a hooked tail.
    pts=[(-.64,-.39,.73),(-1.09,-.05,.92),(-1.20,.70,1.02),(-.68,1.23,1.10),(.10,1.38,1.15),(.82,1.03,1.12),(1.05,.46,1.04),(.94,-.08,.92)]
    b.tube(pts,[.30,.32,.27,.25,.23,.18,.12,.018],'mire',8)
    b.tube([(-.66,-.23,.73),(-.14,-.41,.58),(.42,-.71,.83)],[.28,.30,.28],'dark',7)
    for s in (-1,1):
        b.tube([(.15+s*.19,-.47,.60),(.44+s*.22,-.61,.28),(.64+s*.24,-.88,.07)],[.15,.10,.13],'fang',6)
    b.prism([(.19,-.61),(.14,-1.20),(.47,-1.45),(.80,-1.17),(.69,-.56)],.71,1.14,'fang',axis='z')
    b.cup((.19,-.35,1.03),.16,.59,'mire',7,1.15,.05); b.cup((.66,-.24,1.0),.19,.77,'mire',7,1.1,.06)
    for x in (.31,.59): b.tube([(x,-1.16,.73),(x,-1.28,1.09)],[.07,.005],'bone',6)
    for x in (-.12,.10): b.prism([(x-.05,.60),(x+.09,.99),(x+.03,1.25),(x-.14,.85)],-.63,-.55,'ember',glow=True)
    b.object('body',r); socket(r,'socket_attack',(.46,-1.48,.96)); socket(r,'socket_core',(-.08,-.45,.91)); return r

def boss():
    r=root('boss'); b=Mesh()
    # Bell front and back are open around the swinging clapper; broken right shoulder.
    for s in (-1,1):
        b.tube([(s*.93,.10,1.02),(s*1.16,.28,.44),(s*.94,-.03,.12)],[.24,.17,.27],'dark',7)
    n=12; vs=[]
    for radius,z in ((.58,3.89),(.93,3.09),(1.05,1.80),(1.43,1.02),(1.23,1.02),(.86,1.85),(.73,3.10),(.43,3.82)):
        for j in range(n):
            a=j*math.tau/n; vs.append((radius*math.cos(a),radius*.73*math.sin(a),z))
    fs=[]
    for k in range(7):
        for j in range(n):
            # Two front sectors are missing, framing the clapper through both height and depth.
            if j not in (8,9): fs.append((k*n+j,k*n+(j+1)%n,(k+1)*n+(j+1)%n,(k+1)*n+j))
    b.add(vs,fs,'boss')
    b.tube([(-1.18,.08,2.96),(-1.40,.16,3.94),(-.71,.26,4.50),(.27,.28,4.60),(.66,.26,4.33)],[.21,.19,.19,.16,.10],'teal',7)
    b.box((.96,.14,3.43),(.60,.78,.41),'brass',.08); b.object('body',r)
    for s,name in [(-1,'arm_l'),(1,'arm_r')]:
        a=Mesh(); a.tube([(s*.97,0,2.90),(s*1.49,-.12,2.25),(s*1.71,-.42,1.78)],[.20,.21,.24],'dark',7)
        a.box((s*1.72,-.45,1.75),(.77,.85,.80),'brass',.10)
        for dx in (-.18,.18): a.box((s*1.72+dx,-.81,1.39),(.22,.32,.50),'boss',.035)
        a.object(name,r,(s*.99,0,2.90))
    c=Mesh(); c.tube([(0,0,3.65),(0,-.07,1.75)],.10,'brass',7)
    c.ellipsoid((0,-.12,1.69),(.34,.28,.46),'ember',8,3,True); c.object('clapper',r,(0,0,3.65))
    socket(r,'socket_attack',(0,-1.15,1.77)); socket(r,'socket_core',(0,-.13,1.70)); return r

BASES=dict(ember=ember,thorn=thorn,volt=volt,mire=mire,fang=fang,moth=moth)
EVOLVED=dict(pyre=pyre,storm=storm,dusk=dusk,solar=solar,world=world,eclipse=eclipse,boss=boss)
