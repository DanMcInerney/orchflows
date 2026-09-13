"""Original Nightbind low-poly mesh authoring helpers. Blender 5.2 Python."""
import bpy, math
from mathutils import Vector

PALETTE = dict(night='#101C23', dark='#1C343D', slate='#283E42', teal='#3F696B',
 bone='#D9D3B8', ivory='#EEE2BB', brass='#9B7852', glow='#F1CF82',
 ember='#E69A55', fang='#C48371', thorn='#9DAB72', moth='#D4C58D',
 volt='#75BFD7', mire='#AC8CBB', boss='#AD95B2')

def linear(c):
    c=c.lstrip('#'); rgb=[int(c[i:i+2],16)/255 for i in (0,2,4)]
    return tuple(v/12.92 if v<=.04045 else ((v+.055)/1.055)**2.4 for v in rgb)+(1,)

def material(name, glow=False):
    m=bpy.data.materials.get(name) or bpy.data.materials.new(name)
    m.use_nodes=True; nt=m.node_tree; nt.nodes.clear()
    out=nt.nodes.new('ShaderNodeOutputMaterial'); p=nt.nodes.new('ShaderNodeBsdfPrincipled')
    col=nt.nodes.new('ShaderNodeVertexColor'); col.layer_name='Color'
    nt.links.new(col.outputs['Color'],p.inputs['Base Color'])
    p.inputs['Roughness'].default_value=.86; p.inputs['Metallic'].default_value=.08
    if glow:
        # glTF has no vertex-color emission channel; use an explicit portable amber factor.
        p.inputs['Emission Color'].default_value=linear(PALETTE['glow'])
        p.inputs['Emission Strength'].default_value=.7
    nt.links.new(p.outputs['BSDF'],out.inputs['Surface'])
    return m

class Mesh:
    def __init__(self): self.v=[]; self.f=[]; self.c=[]; self.g=[]
    def add(self,verts,faces,color,glow=False):
        o=len(self.v); self.v.extend(verts); self.f.extend(tuple(i+o for i in f) for f in faces)
        self.c.extend([PALETTE.get(color,color)]*len(faces)); self.g.extend([int(glow)]*len(faces))
        return self
    def box(self,center,size,color,bevel=0):
        x,y,z=center; a,b,c=[v/2 for v in size]
        if bevel:
            pts=[(-a+bevel,-b),(a-bevel,-b),(a,-b+bevel),(a,b-bevel),(a-bevel,b),(-a+bevel,b),(-a,b-bevel),(-a,-b+bevel)]
            return self.prism([(x+u,y+v) for u,v in pts],z-c,z+c,color,axis='z')
        vs=[(x+u*a,y+v*b,z+w*c) for w in (-1,1) for v in (-1,1) for u in (-1,1)]
        return self.add(vs,[(0,2,3,1),(4,5,7,6),(0,1,5,4),(1,3,7,5),(3,2,6,7),(2,0,4,6)],color)
    def prism(self,outline,lo,hi,color,axis='y',glow=False):
        # Counterclockwise polygon in the two visible coordinates; closed thickness.
        def pt(a,b,d): return (a,d,b) if axis=='y' else (a,b,d)
        n=len(outline); vs=[pt(a,b,d) for d in (lo,hi) for a,b in outline]
        fs=[tuple(reversed(range(n))),tuple(range(n,2*n))]
        fs += [(i,(i+1)%n,(i+1)%n+n,i+n) for i in range(n)]
        return self.add(vs,fs,color,glow)
    def ellipsoid(self,c,s,color,n=8,rings=3,glow=False):
        vs=[(c[0],c[1],c[2]-s[2])]
        for k in range(1,rings+1):
            a=-math.pi/2+math.pi*k/(rings+1)
            for j in range(n):
                t=2*math.pi*j/n
                vs.append((c[0]+s[0]*math.cos(a)*math.cos(t),c[1]+s[1]*math.cos(a)*math.sin(t),c[2]+s[2]*math.sin(a)))
        vs.append((c[0],c[1],c[2]+s[2])); top=len(vs)-1
        fs=[(0,1+(j+1)%n,1+j) for j in range(n)]
        for k in range(rings-1):
            for j in range(n):
                a=1+k*n+j; b=1+k*n+(j+1)%n; fs.append((a,b,b+n,a+n))
        fs += [(top,1+(rings-1)*n+j,1+(rings-1)*n+(j+1)%n) for j in range(n)]
        return self.add(vs,fs,color,glow)
    def tube(self,points,radii,color,n=6,closed=True,glow=False):
        vs=[]
        for i,p in enumerate(points):
            tangent=Vector(points[min(i+1,len(points)-1)])-Vector(points[max(0,i-1)])
            tangent.normalize(); u=tangent.cross(Vector((0,1,0)))
            if u.length<.1: u=tangent.cross(Vector((0,0,1)))
            u.normalize(); v=tangent.cross(u).normalized()
            rad=radii[i] if isinstance(radii,list) else radii
            for j in range(n):
                t=j*math.tau/n; vs.append(tuple(Vector(p)+rad*(u*math.cos(t)+v*math.sin(t))))
        fs=[]
        for i in range(len(points)-1):
            for j in range(n): fs.append((i*n+j,i*n+(j+1)%n,(i+1)*n+(j+1)%n,(i+1)*n+j))
        if closed: fs=[tuple(reversed(range(n)))]+fs+[tuple(range((len(points)-1)*n,len(points)*n))]
        return self.add(vs,fs,color,glow)
    def cup(self,center,radius,height,color,n=8,flare=1,thick=.08,axis='z'):
        # Modeled interior and lip, deliberately no cap at the mouth.
        x,y,z=center; vs=[]
        for r,h in ((radius*.65,0),(radius*flare,height),(max(.01,radius*flare-thick),height),(max(.01,radius*.65-thick),thick)):
            for j in range(n):
                a=j*math.tau/n
                vs.append((x+r*math.cos(a),y+r*math.sin(a),z+h) if axis=='z' else (x+r*math.cos(a),y-h,z+r*math.sin(a)))
        fs=[]
        for k in range(3):
            for j in range(n): fs.append((k*n+j,k*n+(j+1)%n,(k+1)*n+(j+1)%n,(k+1)*n+j))
        fs.append(tuple(reversed(range(n)))); fs.append(tuple(range(3*n,4*n)))
        return self.add(vs,fs,color)
    def object(self,name,root,pivot=(0,0,0)):
        me=bpy.data.meshes.new(name+'_mesh'); me.from_pydata([tuple(Vector(v)-Vector(pivot)) for v in self.v],[],self.f); me.update()
        obj=bpy.data.objects.new(name,me); bpy.context.collection.objects.link(obj); obj.parent=root; obj.location=pivot
        me.materials.append(material('Painted reliquary')); use_glow=any(self.g)
        if use_glow: me.materials.append(material('Bound light',True))
        colors=me.color_attributes.new(name='Color',type='FLOAT_COLOR',domain='CORNER')
        for poly,col,g in zip(me.polygons,self.c,self.g):
            poly.material_index=g
            for li in poly.loop_indices: colors.data[li].color=linear(col)
        # Correct concave prism triangulation and recalculate all outward normals.
        bpy.context.view_layer.objects.active=obj; obj.select_set(True)
        bpy.ops.object.mode_set(mode='EDIT'); bpy.ops.mesh.select_all(action='SELECT'); bpy.ops.mesh.normals_make_consistent(inside=False); bpy.ops.object.mode_set(mode='OBJECT'); obj.select_set(False)
        return obj

def root(name):
    o=bpy.data.objects.new(name,None); bpy.context.collection.objects.link(o); return o

def socket(parent,name,pos):
    o=bpy.data.objects.new(name,None); bpy.context.collection.objects.link(o); o.parent=parent; o.location=pos
    # Standard exporter conversion supplies Y-up/+Z-forward; attachment nodes stay neutral.
    o.rotation_euler=(0,0,0); o.empty_display_type='ARROWS'; o.empty_display_size=.18
    return o

def scaled(points,sx=1,sy=1,sz=1): return [(x*sx,y*sy,z*sz) for x,y,z in points]
