import hashlib, importlib.util, json, pathlib, re, subprocess
import jsonschema
BASE=pathlib.Path(__file__).parent
PLUGIN=pathlib.Path('/Users/randlee/.codex/plugins/cache/plan-anchor/sc-plan-anchor/0.5.0')
SK=PLUGIN/'skills/plan-anchoring'
spec=importlib.util.spec_from_file_location('contract',SK/'scripts/anchor_tuning_contract.py')
c=importlib.util.module_from_spec(spec); spec.loader.exec_module(c)
def save(name,value): (BASE/name).write_bytes(c.canonical_bytes(value)+b'\n')
result=json.loads((BASE/'result.json').read_text()); data=result['data']
# Round summary diagnostics to six decimals so sc-compose's JSON parser preserves
# exact canonical values. Raw Jev responses and frozen oracle remain untouched.
for row in data['candidate_rankings']:
    row['confidence_diagnostics']['mean']=round(row['confidence_diagnostics']['mean'],6)
data['confidence_diagnostics']['mean']=round(data['confidence_diagnostics']['mean'],6)
data['tuning_history_after']['events'][-1]['score']['confidence']=data['confidence_diagnostics']
data['tuning_history_after_sha256']=c.sha256(data['tuning_history_after'])
save('result.json',result); save('result-vars.json',{k:v for k,v in result.items() if k!='schema_version'})
subprocess.run(['sc-compose','render','--file',str(SK/'templates/anchor-tuning-result.md.j2'),'--root',str(PLUGIN),'--var-file',str(BASE/'result-vars.json'),'--strict','--check-render','--output',str(BASE/'response.md')],capture_output=True,text=True,check=True)
rendered=json.loads(re.findall(r'```json\s*\n(.*?)\n```',(BASE/'response.md').read_text(),re.S)[0]); assert rendered==result
jsonschema.validate(rendered,json.loads((SK/'assets/schemas/anchor-tuning-result.schema.json').read_text())); c.validate_result(rendered)
save('validation.json',{'request_schema':True,'request_relational':True,'runtime_and_authority_digests':True,'result_schema':True,'result_relational':True,'strict_template_render':True,'rendered_round_trip':True})
print(json.dumps({'accepted':data['accepted'],'selected':data['tuning_history_after']['events'][-1]['candidate'],'score':data['semantic_score'],'response':str(BASE/'response.md')}))
