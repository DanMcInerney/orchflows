"""Remaining restrained bell-court kit; all visual and nonblocking."""
import math
from meshkit import Mesh,root,socket

def arena_floor():
    r=root('arena_floor'); b=Mesh(); n=64
    b.add([(0,0,0)]+[(12*math.cos(j*math.tau/n),12*math.sin(j*math.tau/n),0) for j in range(n)],[(0,j+1,(j+1)%n+1) for j in range(n)],'dark')
    for course,(r0,r1) in enumerate([(12,15),(15,17.75),(17.75,20.2)]):
        for j in range(n):
            a0=j*math.tau/n; a1=(j+1)*math.tau/n
            col=['#233C41','#263F43','#294146'][((j//8)+course)%3]
            b.add([(rad*math.cos(a),rad*math.sin(a),0) for rad,a in [(r0,a0),(r1,a0),(r1,a1),(r0,a1)]],[(0,1,2,3)],col)
    # Low underside and outer edge, no duplicated high-sided cylinder.
    for j in range(n):
        a0=j*math.tau/n; a1=(j+1)*math.tau/n
        b.add([(20.2*math.cos(a),20.2*math.sin(a),z) for a,z in [(a0,0),(a0,-.6),(a1,-.6),(a1,0)]],[(0,1,2,3)],'night')
    b.add([(20.2*math.cos(j*math.tau/n),20.2*math.sin(j*math.tau/n),-.6) for j in range(n)],[tuple(reversed(range(n)))],'night')
    for radius in (12.1,17.8):
        for j in range(24):
            if j%3==2: continue
            a0=j*math.tau/24+.02; a1=(j+1)*math.tau/24-.04
            b.add([(rad*math.cos(a),rad*math.sin(a),.006) for rad,a in [(radius,a0),(radius+.045,a0),(radius+.045,a1),(radius,a1)]],[(0,1,2,3)],'#655C49')
    b.object('body',r); return r

def shrine_plinth():
    r=root('shrine_plinth'); b=Mesh()
    b.box((0,0,.13),(2.4,1.8,.26),'slate',.14); b.box((0,.08,.58),(1.93,1.38,.76),'teal',.13)
    b.prism([(-1.12,.93),(-.82,1.25),(.82,1.25),(1.12,.93)],-.77,.78,'slate')
    b.box((0,-.655,.60),(1.14,.07,.43),'night',.05)
    b.box((0,-.70,.60),(.31,.03,.30),'brass',.06)
    b.object('body',r); return r

def votive():
    r=root('votive'); b=Mesh(); b.box((0,0,.10),(.70,.70,.20),'slate',.08)
    b.prism([(-.25,.2),(-.20,1.15),(.20,1.15),(.25,.2)],-.20,.23,'teal')
    for s in (-1,1): b.box((s*.23,0,1.24),(.12,.44,.55),'slate')
    b.prism([(-.35,1.45),(0,1.65),(.35,1.45)],-.30,.30,'brass')
    b.box((0,.17,1.26),(.38,.08,.38),'night')
    b.ellipsoid((0,-.04,1.23),(.105,.09,.16),'glow',6,2,True); b.object('body',r); return r

def rubble_cluster():
    r=root('rubble_cluster'); b=Mesh()
    for cx,cy,w,d,h in [(-.48,.12,1.04,.72,.28),(.52,.10,.96,.61,.35),(.06,-.38,.61,.34,.17)]:
        b.prism([(cx-w/2,cy-d/3),(cx-w*.32,cy-d/2),(cx+w*.42,cy-d/2),(cx+w/2,cy+d*.26),(cx+w*.28,cy+d/2),(cx-w/2,cy+d*.36)],0,h,'slate',axis='z')
    b.object('body',r); return r

ENVIRONMENT=dict(arena_floor=arena_floor,shrine_plinth=shrine_plinth,votive=votive,rubble_cluster=rubble_cluster)
