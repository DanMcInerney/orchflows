"""Open representative frozen Blender sources without saving or exporting."""
import bpy, json
from pathlib import Path
root=Path(__file__).resolve().parents[2]
rows=[]
for name in ('keeper-assembly','arch-rim-assembly','storm','solar','boss'):
    bpy.ops.wm.open_mainfile(filepath=str(root/'assets/source'/f'{name}.blend'))
    objects=[]
    for o in bpy.data.objects:
        objects.append({'name':o.name,'type':o.type,'parent':o.parent.name if o.parent else None,'vertices':len(o.data.vertices) if o.type=='MESH' else None})
    rows.append({'source':f'assets/source/{name}.blend','objects':objects,'meshCount':sum(o.type=='MESH' for o in bpy.data.objects),'materials':list(bpy.data.materials.keys())})
out={'result':'PASS','blender':bpy.app.version_string,'method':'Opened five saved source files and inspected editable mesh objects, parent hierarchy and materials; no saving or export','sources':rows}
(Path(__file__).resolve().parent/'blender-source-inspection.json').write_text(json.dumps(out,indent=2)+'\n',encoding='utf-8')
print(json.dumps({'result':'PASS','sources':[{k:r[k] for k in ('source','meshCount')} for r in rows]}))
