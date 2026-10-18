"""Correct envelope timing from persisted request/response timestamps, offline."""
import datetime, hashlib, importlib.util, json, pathlib, re, subprocess
import jsonschema
root=pathlib.Path(__file__).resolve().parent
plugin=pathlib.Path('/Users/randlee/.codex/plugins/cache/plan-anchor/sc-plan-anchor/0.5.0')
skill=plugin/'skills/plan-anchoring'
def canonical(value):return json.dumps(value,sort_keys=True,separators=(',',':'),ensure_ascii=False).encode()
def sha(value):return hashlib.sha256(canonical(value)).hexdigest()
def save(name,value):(root/name).write_bytes(canonical(value)+b'\n')
result=json.loads((root/'result.json').read_text());before_data=sha(result['data'])
runs=json.loads((root/'runs.json').read_text())
files=[]
for run in runs:
    for suffix in ['-request.json','-response-a'+str(run['attempts'])+'.json']:
        p=root/(run['run_id']+suffix)
        files.append({'file':p.name,'mtime_ns':p.stat().st_mtime_ns,'sha256':hashlib.sha256(p.read_bytes()).hexdigest(),'kind':'request' if suffix=='-request.json' else 'response'})
first=min((f for f in files if f['kind']=='request'),key=lambda f:f['mtime_ns'])
last=max((f for f in files if f['kind']=='response'),key=lambda f:f['mtime_ns'])
elapsed_ns=last['mtime_ns']-first['mtime_ns'];assert elapsed_ns>0
duration_ms=elapsed_ns//1_000_000
proof={'method':'Filesystem modification timestamp of first persisted canonical request through last persisted raw response. The runner persists requests before calls and responses immediately after calls; no new Jev request was made.','request_count':len(runs),'start':first,'end':last,'elapsed_ns':elapsed_ns,'duration_ms':duration_ms,'rounding':'floor nanoseconds to whole milliseconds','files':files,'data_sha256_before':before_data}
result['metadata']['duration_ms']=duration_ms
assert sha(result['data'])==before_data
spec=importlib.util.spec_from_file_location('contract',skill/'scripts/anchor_tuning_contract.py');contract=importlib.util.module_from_spec(spec);spec.loader.exec_module(contract)
schema=json.loads((skill/'assets/schemas/anchor-tuning-result.schema.json').read_text())
jsonschema.validate(result,schema);contract.validate_result(result)
save('duration-proof.json',proof);save('result.json',result);save('result-vars.json',{k:v for k,v in result.items() if k!='schema_version'})
subprocess.run(['sc-compose','render','--strict','--check-render','--root',str(plugin),'--file',str(skill/'templates/anchor-tuning-result.md.j2'),'--var-file',str(root/'result-vars.json'),'--output',str(root/'response.md')],check=True,capture_output=True,text=True)
rendered=json.loads(re.findall(r'```json\s*\n(.*?)\n```',(root/'response.md').read_text(),re.S)[0]);assert rendered==result
jsonschema.validate(rendered,schema);contract.validate_result(rendered)
assert sha(rendered['data'])==before_data
save('result-validation.json',{'schema':True,'contract':True,'strict_template_render':True,'result_sha256':sha(rendered),'data_sha256_before':before_data,'data_sha256_after':sha(rendered['data']),'duration_proof':'duration-proof.json'})
print(json.dumps({'duration_ms':duration_ms,'start':first,'end':last,'elapsed_ns':elapsed_ns,'data_unchanged':True,'response':str(root/'response.md'),'result':str(root/'result.json'),'proof':str(root/'duration-proof.json')}))
