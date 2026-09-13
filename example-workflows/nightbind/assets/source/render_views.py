"""Source contact inspection and portraits reimported from delivered GLBs."""
import bpy,sys,math,argparse,json
from pathlib import Path
from mathutils import Vector
HERE=Path(__file__).resolve().parent; PROJECT=HERE.parent.parent

def setup(size=600,transparent=False):
    sc=bpy.context.scene; sc.render.engine='CYCLES'; sc.cycles.device='CPU'; sc.cycles.samples=16
    sc.render.resolution_x=size; sc.render.resolution_y=size; sc.render.resolution_percentage=100
    sc.render.image_settings.file_format='PNG'; sc.render.image_settings.color_mode='RGBA'; sc.render.film_transparent=transparent
    sc.world.color=(.11,.15,.18); sc.view_settings.view_transform='AgX'
    for name,loc,power,color,size in [('key',(-6,-9,12),1700,(1,.84,.61),8),('fill',(8,-2,8),900,(.54,.72,1),7),('rim',(0,6,9),1600,(.48,.72,1),5)]:
        data=bpy.data.lights.new(name,'AREA'); data.energy=power; data.color=color; data.shape='DISK'; data.size=size
        o=bpy.data.objects.new(name,data); bpy.context.collection.objects.link(o); o.location=loc; o.rotation_euler=(Vector((0,0,1))-o.location).to_track_quat('-Z','Y').to_euler()
    data=bpy.data.cameras.new('Inspection camera'); camera=bpy.data.objects.new('Inspection camera',data); bpy.context.collection.objects.link(camera); sc.camera=camera; data.type='ORTHO'
    return camera

def shot(camera,loc,target,scale,path):
    camera.location=loc; camera.rotation_euler=(Vector(target)-camera.location).to_track_quat('-Z','Y').to_euler(); camera.data.ortho_scale=scale
    bpy.context.scene.render.filepath=str(path); bpy.ops.render.render(write_still=True)

def import_glb(name):
    prior=set(bpy.data.objects); bpy.ops.import_scene.gltf(filepath=str(PROJECT/'public/models'/f'{name}.glb'))
    return [o for o in bpy.data.objects if o not in prior]

def source_representatives():
    bpy.ops.wm.open_mainfile(filepath=str(HERE/'keeper.blend'))
    # A second copy from its actual GLB hangs at the source keeper socket.
    objs=import_glb('lantern')
    for o in objs:
        if o.parent is None: o.location=(.76,-.45,.36)
    camera=setup()
    out=PROJECT/'evidence/assets'
    for name,loc in [('front',(0,-9,1.1)),('side',(9,0,1.1)),('three-quarter',(6,-9,6)),('game-angle',(0,-28,36))]:
        shot(camera,loc,(.22,0,1.04),3.5,out/f'keeper-source-{name}.png')
    bpy.ops.wm.save_as_mainfile(filepath=str(HERE/'keeper-assembly.blend'))
    bpy.ops.wm.open_mainfile(filepath=str(HERE/'bell_arch.blend'))
    objs=import_glb('hanging_bell')
    for o in objs:
        if o.parent is None: o.location=(0,0,5.02)
    for i in range(2):
        objs=import_glb('rim_segment')
        for o in objs:
            if o.parent is None:
                o.rotation_mode='XYZ'; o.rotation_euler.z=math.radians(15-i*15); o.location=(0,-20.4,0)
    camera=setup(800)
    shot(camera,(10,-17,13),(0,0,2.65),10.2,out/'arch-rim-source-joint.png')
    shot(camera,(0,-28,36),(0,0,2.65),10.2,out/'arch-rim-source-game-angle.png')
    bpy.ops.wm.save_as_mainfile(filepath=str(HERE/'arch-rim-assembly.blend'))
    bpy.ops.wm.open_mainfile(filepath=str(HERE/'boss.blend')); camera=setup(600)
    shot(camera,(7,-12,7),(0,0,2.3),6.1,out/'boss-source-three-quarter.png')
    shot(camera,(0,-28,36),(0,0,2.3),6.1,out/'boss-source-game-angle.png')

def portraits():
    manifest=json.loads((PROJECT/'public/models/manifest.json').read_text())
    for asset in manifest['assets']:
        if 'portrait' not in asset: continue
        bpy.ops.object.select_all(action='SELECT'); bpy.ops.object.delete(use_global=False)
        import_glb(asset['id']); camera=setup(192,True)
        lo=asset['bounds']['min']; hi=asset['bounds']['max']; center=((lo[0]+hi[0])/2,-(lo[2]+hi[2])/2,(lo[1]+hi[1])/2)
        extent=max(hi[i]-lo[i] for i in range(3)); scale=extent*1.34
        shot(camera,(center[0]+6,center[1]-9,center[2]+6),center,scale,PROJECT/'public'/asset['portrait'].lstrip('/'))

def lineups():
    for group,ids,spacing in [('bases',['ember','thorn','volt','mire','fang','moth'],2.4),('evolved',['pyre','storm','dusk','solar','world','eclipse'],3.7)]:
        bpy.ops.object.select_all(action='SELECT'); bpy.ops.object.delete(use_global=False)
        for k,name in enumerate(ids):
            with bpy.data.libraries.load(str(HERE/f'{name}.blend'),link=False) as (src,dst): dst.objects=src.objects
            for o in dst.objects:
                bpy.context.collection.objects.link(o)
                if o.parent is None: o.location.x=(k-(len(ids)-1)/2)*spacing
        camera=setup(1400); bpy.context.scene.render.resolution_y=420
        for mode,loc in [('front',(0,-22,1.3)),('game-angle',(0,-28,36)),('three-quarter',(5,-24,15))]:
            shot(camera,loc,(0,0,1),len(ids)*spacing,PROJECT/'evidence/assets'/f'{group}-source-{mode}.png')

if __name__=='__main__':
    parser=argparse.ArgumentParser(); parser.add_argument('--portraits',action='store_true'); parser.add_argument('--lineups',action='store_true'); args=parser.parse_args(sys.argv[sys.argv.index('--')+1:] if '--' in sys.argv else [])
    portraits() if args.portraits else lineups() if args.lineups else source_representatives()
