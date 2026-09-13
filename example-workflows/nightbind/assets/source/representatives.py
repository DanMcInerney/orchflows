"""Keeper and the joined drowned-bell court kit; original authored geometry."""
import math
from meshkit import Mesh,root,socket

def keeper():
    r=root('keeper'); b=Mesh()
    # Two shaped cloak leaves preserve a dark split, inset feet and a wide mantle.
    for s in (-1,1):
        b.prism([(s*.10,.14),(s*.55,.20),(s*.49,.85),(s*.38,1.39),(s*.05,1.28)],-.22,.28,'teal')
        b.prism([(s*.12,.33),(s*.49,.27),(s*.39,1.21),(s*.13,1.15)],-.26,-.22,'bone')
        b.box((s*.23,-.16,.09),(.22,.45,.18),'night',.05)
    b.prism([(-.67,1.27),(-.55,1.55),(-.25,1.67),(.25,1.67),(.55,1.55),(.67,1.27),(.28,1.19),(-.28,1.19)],-.25,.25,'ivory')
    # Hood uses a forward projecting forehead and side planes around a black cavity.
    b.prism([(-.33,1.50),(-.36,1.83),(-.16,2.10),(.16,2.10),(.34,1.85),(.32,1.50)],-.12,.32,'teal')
    b.prism([(-.26,1.54),(-.27,1.83),(0,1.99),(.26,1.83),(.24,1.54)],-.37,-.13,'night')
    b.prism([(-.37,1.78),(-.17,2.10),(.17,2.10),(.37,1.78),(.25,1.83),(0,1.97),(-.25,1.83)],-.45,-.10,'bone')
    b.box((0,-.32,1.10),(.24,.12,.18),'brass',.035)
    b.object('body',r)
    arm=Mesh(); arm.tube([(.50,0,1.38),(.64,-.04,1.06),(.63,-.39,1.10)],[.13,.11,.09],'teal',6)
    arm.ellipsoid((.63,-.43,1.10),(.105,.105,.10),'bone',6,2); arm.object('arm_r',r,(.50,0,1.38))
    socket(r,'socket_lantern',(.76,-.45,.36)); socket(r,'socket_capture',(.76,-.45,.81)); socket(r,'socket_attack',(0,-.48,1.32))
    return r

def lantern():
    r=root('lantern'); b=Mesh()
    b.box((0,0,.10),(.65,.57,.16),'brass',.10); b.box((0,0,.68),(.57,.49,.10),'brass',.08)
    for x in (-.225,.225):
        for y in (-.18,.18): b.tube([(x,y,.15),(x*.94,y*.94,.62)],.027,'brass',4)
    b.tube([(-.14,0,.73),(-.14,0,.84),(0,0,.92),(.14,0,.84),(.14,0,.73)],.025,'brass',4)
    b.ellipsoid((0,0,.41),(.14,.12,.20),'glow',8,3,True); b.object('body',r)
    socket(r,'socket_core',(0,0,.42)); return r

def rim_segment():
    r=root('rim_segment'); b=Mesh(); vs=[]
    n=3
    for radius,z in ((19.7,0),(21.1,0),(19.7,.14),(21.1,.23)):
        for i in range(n+1):
            a=math.radians(i*15/n); vs.append((math.sin(a)*radius,math.cos(a)*radius,z))
    fs=[]
    for i in range(n):
        fs.extend([(i,i+1,i+1+4,i+4),(i+8,i+12,i+13,i+9),(i,i+8,i+9,i+1),(i+4,i+5,i+13,i+12)])
    fs.extend([(0,4,12,8),(3,11,15,7)]); b.add(vs,fs,'slate')
    for a0,a1 in ((1,6.5),(8.5,14)):
        pts=[]
        for rad in (20.10,20.18):
            for a in (a0,a1): pts.append((rad*math.sin(math.radians(a)),rad*math.cos(math.radians(a)),.185))
        b.add(pts,[(0,1,3,2)],'brass')
    b.object('body',r); socket(r,'socket_start',(0,20.4,0)); socket(r,'socket_end',(20.4*math.sin(math.pi/12),20.4*math.cos(math.pi/12),0)); return r

def bell_arch():
    r=root('bell_arch'); b=Mesh()
    # Deliberately unequal piers and broken shoulders, with a crown held by a brass tie.
    for s,h in ((-1,4.45),(1,4.08)):
        b.box((s*2.43,0,.20),(1.34,1.60,.40),'slate',.16)
        b.prism([(s*2.92,.40),(s*2.86,h),(s*2.25,h+.25),(s*1.99,.40)],-.53,.55,'teal')
        b.box((s*2.45,-.03,1.45),(1.0,1.17,.14),'brass',.06)
        b.box((s*2.46,0,3.45),(.90,1.16,.18),'brass',.06)
    b.prism([(-2.89,4.15),(-2.33,5.16),(-1.31,5.73),(-.26,5.80),(-.09,5.31),(-1.10,5.18),(-1.87,4.74),(-2.03,4.03)],-.49,.49,'slate')
    b.prism([(.18,5.30),(.40,5.79),(1.50,5.60),(2.41,4.95),(2.84,4.12),(2.04,3.89),(1.87,4.59),(1.25,5.08)],-.49,.49,'teal')
    b.box((0,-.02,5.47),(1.13,.66,.18),'brass',.05)
    b.tube([(0,0,5.37),(0,0,4.95)],.065,'brass',6)
    b.object('body',r); socket(r,'socket_bell',(0,0,5.02)); return r

def hanging_bell():
    r=root('hanging_bell'); b=Mesh()
    # Root is at suspension; ring courses flare down and have a real inner skin.
    vs=[]; n=10
    for radius,z in ((.25,-.10),(.45,-.50),(.61,-1.25),(.80,-1.60),(.68,-1.60),(.50,-1.22),(.34,-.52)):
        for j in range(n):
            a=j*math.tau/n; vs.append((radius*math.cos(a),radius*.94*math.sin(a),z+(.12 if j==2 and z<-1 else 0)))
    fs=[]
    for k in range(6):
        for j in range(n):
            if not(j==2 and k>=2): fs.append((k*n+j,k*n+(j+1)%n,(k+1)*n+(j+1)%n,(k+1)*n+j))
    b.add(vs,fs,'brass'); b.tube([(0,0,-.15),(0,0,-1.35)],.06,'night',5)
    b.ellipsoid((0,0,-1.5),(.14,.14,.18),'glow',6,2); b.object('body',r); return r

REPRESENTATIVES=dict(keeper=keeper,lantern=lantern,rim_segment=rim_segment,bell_arch=bell_arch,hanging_bell=hanging_bell)
