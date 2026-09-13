from pathlib import Path
import json, statistics, sys
source=Path(sys.argv[1])
data=json.loads(source.read_text(encoding='utf-8-sig'))
if isinstance(data,list):
    metadata=json.loads(Path(sys.argv[2]).read_text(encoding='utf-8-sig'))
    data={**metadata,'frames':data}
fields=data['fields']; rows=[dict(zip(fields,row)) for row in data['frames']]
def percentile(values,p):
    values=sorted(values)
    if not values: return None
    pos=(len(values)-1)*p; low=int(pos); high=min(low+1,len(values)-1)
    return round(values[low]*(high-pos)+values[high]*(pos-low),3) if high != low else round(values[low],3)
def summarize(group):
    if not group: return {'samples':0}
    ms=[row['rawFrameMs'] for row in group]
    return {'samples':len(group),'rawWallSeconds':round(sum(ms)/1000,3),'simulatedInterval':[group[0]['time'],group[-1]['time']], 'medianMs':percentile(ms,.5),'p95Ms':percentile(ms,.95),'p99Ms':percentile(ms,.99),'worstMs':max(ms),'over50ms':sum(x>50 for x in ms),'over100ms':sum(x>100 for x in ms),'over200ms':sum(x>200 for x in ms),'hostilesMax':max(row['hostiles'] for row in group),'callsMax':max(row['calls'] for row in group),'trianglesMax':max(row['triangles'] for row in group)}
runs=sorted({row['run'] for row in rows})
result={'build':data['build'],'source':str(source),'backend':data.get('backend'),'viewport':data.get('viewport'),'load':{'readyAtMs':data.get('readyAtMs'),'assetLoadDurationMs':data.get('loadDurationMs'),'meaning':'Asset/portrait readiness in application clock, excludes first-frame shader compilation; browser-observed title boot also required.'}, 'frameColumns':fields,'runs':{}}
for run in runs:
    group=[row for row in rows if row['run']==run]
    result['runs'][str(run)]={'allLive':summarize(group),'byWave':{str(w):summarize([row for row in group if row['wave']==w]) for w in sorted({r['wave'] for r in group})},'firstPressure':summarize([row for row in group if 74<=row['time']<88]),'latePressure':summarize([row for row in group if 184<=row['time']<198]),'busyAtLeast60':summarize([row for row in group if row['hostiles']>=60])}
print(json.dumps(result,indent=2))
