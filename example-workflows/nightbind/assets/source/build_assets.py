"""Reproducible original Blender source/GLB/manifest production.
blender --background --factory-startup --python assets/source/build_assets.py -- --stage representatives
"""
import bpy,sys,os,json,struct,hashlib,math,argparse
from pathlib import Path
from mathutils import Matrix,Vector,Quaternion
HERE=Path(__file__).resolve().parent; PROJECT=HERE.parent.parent
sys.path.insert(0,str(HERE))
from representatives import REPRESENTATIVES

TARGETS=dict(ember=(1.05,1.35,.95),thorn=(1.4,1.25,1.3),volt=(1.8,1.1,1.15),mire=(1.35,1.1,1.4),fang=(1.05,1.2,1.55),moth=(1.7,1.2,1.15),pyre=(2.1,2.35,1.65),storm=(2.65,1.7,2.0),dusk=(2.35,2.35,1.9),solar=(3.25,2.7,2.25),world=(3.15,2.3,2.7),eclipse=(3,2.7,2.55),boss=(4.2,4.6,3.4))

def fit_authored_bounds(r):
    if r.name not in TARGETS: return
    objs=list(r.children_recursive); points=[o.matrix_world@v.co for o in objs if o.type=='MESH' for v in o.data.vertices]
    lo=[min(p[i] for p in points) for i in range(3)]; hi=[max(p[i] for p in points) for i in range(3)]
    target=TARGETS[r.name]; dims=(target[0],target[2],target[1]); factor=[dims[i]/(hi[i]-lo[i]) for i in range(3)]
    # Authored proportions are fitted once in source, never with non-unit export roots.
    shift=[-(lo[0]+hi[0])/2,-(lo[1]+hi[1])/2,-lo[2]]
    for o in objs:
        if o.type=='MESH':
            for v in o.data.vertices: v.co=[v.co[i]*factor[i] for i in range(3)]
        o.location=[(o.location[i]+shift[i])*factor[i]+(.12 if i==2 and r.name in ('volt','moth','solar') else 0) for i in range(3)]
    bpy.context.view_layer.update()

def inspect_glb(path,source):
    data=path.read_bytes(); jlen=struct.unpack_from('<I',data,12)[0]; doc=json.loads(data[20:20+jlen]); binary=data[28+jlen:]
    lo=[float('inf')]*3; hi=[-float('inf')]*3; count=0; verts=0; parts=[]; sockets=[]
    nodes=doc.get('nodes',[]); parents={child:i for i,n in enumerate(nodes) for child in n.get('children',[])}
    def transform(n):
        if 'matrix' in n: return Matrix([n['matrix'][i::4] for i in range(4)])
        return Matrix.LocRotScale(Vector(n.get('translation',[0,0,0])),Quaternion([n.get('rotation',[0,0,0,1])[3]]+n.get('rotation',[0,0,0,1])[:3]),Vector(n.get('scale',[1,1,1])))
    def world(i): return world(parents[i])@transform(nodes[i]) if i in parents else transform(nodes[i])
    for i,n in enumerate(nodes):
        loc={k:n.get(k,default) for k,default in [('translation',[0,0,0]),('rotation',[0,0,0,1]),('scale',[1,1,1])]}
        entry=dict(name=n.get('name'),parent=nodes[parents[i]].get('name') if i in parents else None,**loc)
        if n.get('name','').startswith('socket_'): sockets.append(entry)
        if 'mesh' not in n: continue
        partTris=0; partVerts=0
        for p in doc['meshes'][n['mesh']]['primitives']:
            a=doc['accessors'][p['attributes']['POSITION']]; view=doc['bufferViews'][a['bufferView']]; offset=view.get('byteOffset',0)+a.get('byteOffset',0); stride=view.get('byteStride',12)
            for v in range(a['count']):
                pt=world(i)@Vector(struct.unpack_from('<3f',binary,offset+v*stride))
                for ax in range(3): lo[ax]=min(lo[ax],pt[ax]); hi[ax]=max(hi[ax],pt[ax])
            partVerts+=a['count']; partTris+=doc['accessors'][p['indices']]['count']//3 if 'indices' in p else a['count']//3
        motion={'wing_l':'hinged flap','wing_r':'hinged flap','head':'anticipation lean and recoil','jaw':'hinged bite','clapper':'warning swing','arm_r':'subtle hand gesture','arm_l':'warning gesture'}.get(entry['name'],'rigid body')
        parts.append(dict(**entry,triangles=partTris,vertices=partVerts,intendedMotion=motion)); count+=partTris; verts+=partVerts
    asset=dict(id=path.stem,file='/models/'+path.name,source=source,root=path.stem,
        bounds=dict(min=[round(v,5) for v in lo],max=[round(v,5) for v in hi]),triangles=count,vertices=verts,meshParts=parts,
        materials=[dict(name=m.get('name'),alphaMode=m.get('alphaMode','OPAQUE'),roughness=m.get('pbrMetallicRoughness',{}).get('roughnessFactor',1),metallic=m.get('pbrMetallicRoughness',{}).get('metallicFactor',1),doubleSided=m.get('doubleSided',False),emissiveFactor=m.get('emissiveFactor',[0,0,0])) for m in doc.get('materials',[])],
        bytes=len(data),textures=[],animations=[a.get('name','') for a in doc.get('animations',[])],sockets=sockets,motions=[],sha256=hashlib.sha256(data).hexdigest())
    if path.stem not in ('arena_floor','rim_segment','bell_arch','hanging_bell','shrine_plinth','votive','rubble_cluster'):
        asset['portrait']='/models/portraits/'+path.stem+'.png'
        asset['motions']=[dict(state='idle',nodes=[path.stem],axis='Y',range=[-.018,.018],phase='sin(entityTime*3 + entityId)'),dict(state='travel',nodes=[path.stem],axis='Y',range=[-.035,.035],phase='sin(entityTime*8 + entityId)'),dict(state='attack',nodes=['head' if any(p['name']=='head' for p in parts) else 'body'],axis='X',range=[-.12,0],phase='0.16s recoil starting on authoritative damage tick; no action delay')]
    for p in parts:
        if p['name'] in ('wing_l','wing_r'):
            asset['motions'].append(dict(state='idle',nodes=[p['name']],axis='Z',range=[-.314,.314],phase='opposed wings; Volt 11rad/s, Moth 6rad/s'))
        elif p['name'] in ('head','jaw'):
            asset['motions'].append(dict(state='windup',nodes=[p['name']],axis='X',range=[0,.20],phase='existing anticipation timer only; recoil at damage tick'))
        elif p['name']=='clapper':
            asset['motions'].append(dict(state='windup',nodes=['clapper'],axis='X',range=[-.24,.24],phase='existing boss warning; no delayed damage'))
    return asset

def build(which,from_saved=False):
    path=PROJECT/'public/models'; path.mkdir(parents=True,exist_ok=True)
    manifestPath=path/'manifest.json'; prior=json.loads(manifestPath.read_text())['assets'] if manifestPath.exists() else []
    assets={a['id']:a for a in prior}
    for name,fn in which.items():
        src=HERE/(name+'.blend')
        if from_saved:
            bpy.ops.wm.open_mainfile(filepath=str(src)); r=bpy.data.objects[name]
        else:
            bpy.ops.object.select_all(action='SELECT'); bpy.ops.object.delete(use_global=False)
            for material in list(bpy.data.materials): bpy.data.materials.remove(material)
            r=fn(); bpy.context.view_layer.update(); fit_authored_bounds(r)
        bpy.context.scene.unit_settings.system='METRIC'; bpy.context.scene.unit_settings.scale_length=1
        bpy.ops.object.select_all(action='DESELECT')
        for obj in [r]+list(r.children_recursive): obj.select_set(True)
        bpy.ops.wm.save_as_mainfile(filepath=str(src))
        out=path/(name+'.glb')
        bpy.ops.export_scene.gltf(filepath=str(out),export_format='GLB',use_selection=True,export_yup=True,
            export_apply=True,export_animations=False,export_skins=False,export_morph=False,export_cameras=False,
            export_lights=False,export_texcoords=False,export_normals=True,export_vertex_color='MATERIAL',
            export_all_vertex_colors=False,export_materials='EXPORT',export_extras=False)
        assets[name]=inspect_glb(out,'assets/source/'+src.name)
        print('MEASURED',name,assets[name]['triangles'],assets[name]['bytes'],assets[name]['bounds'],flush=True)
    result=dict(schemaVersion=1,blenderVersion=bpy.app.version_string,basis=dict(sourceUp='Z',sourceForward='-Y',runtimeUp='Y',runtimeForward='+Z',units='game-unit'),assets=list(assets.values()))
    manifestPath.write_text(json.dumps(result,indent=2)+'\n')
    (PROJECT/'evidence/assets/export-measurements.json').write_text(json.dumps(result,indent=2)+'\n')

if __name__=='__main__':
    parser=argparse.ArgumentParser(); parser.add_argument('--stage',choices=['representatives','bases','evolved','environment','all'],default='representatives'); parser.add_argument('--from-saved',action='store_true',help='Export edited .blend sources without regenerating geometry')
    args=parser.parse_args(sys.argv[sys.argv.index('--')+1:] if '--' in sys.argv else [])
    which=dict(REPRESENTATIVES)
    if args.stage!='representatives':
        from creatures import BASES,EVOLVED
        from environment import ENVIRONMENT
        which={'bases':BASES,'evolved':EVOLVED,'environment':ENVIRONMENT,'all':dict(**REPRESENTATIVES,**BASES,**EVOLVED,**ENVIRONMENT)}[args.stage]
    build(which,args.from_saved)
