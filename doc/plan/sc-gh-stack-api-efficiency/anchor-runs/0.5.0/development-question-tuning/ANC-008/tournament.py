import concurrent.futures as cf
import copy, hashlib, importlib.util, json, os, pathlib, re, statistics, subprocess, sys, time
import jsonschema

BASE=pathlib.Path(__file__).parent
PLUGIN=pathlib.Path('/Users/randlee/.codex/plugins/cache/plan-anchor/sc-plan-anchor/0.5.0')
SK=PLUGIN/'skills/plan-anchoring'
start=time.monotonic()
def module(name,path):
    spec=importlib.util.spec_from_file_location(name,path)
    m=importlib.util.module_from_spec(spec); sys.modules[name]=m; spec.loader.exec_module(m); return m
# Ignore environment configuration: only the API credential is consumed.
for name in tuple(os.environ):
    if name.startswith('PLAN_ANCHOR_'): del os.environ[name]
j=module('judge',SK/'scripts/jev_judge.py')
c=module('contract',SK/'scripts/anchor_tuning_contract.py')
def save(name,value): (BASE/name).write_bytes(c.canonical_bytes(value)+b'\n')
blocks=re.findall(r'```json\s*\n(.*?)\n```',(BASE/'request.md').read_text(),re.S)
assert len(blocks)==1
p=json.loads(blocks[0]); a=p['authority']['anchors']['records'][0]
jsonschema.validate(p,json.loads((SK/'assets/schemas/anchor-tuning-request.schema.json').read_text())); c.validate_request(p)
for path,digest in [(p['runtime']['script'],p['runtime']['sha256']),(p['runtime']['contract_script'],p['runtime']['contract_sha256']), (PLUGIN/'.codex/agents/anchor-tuning.md','36e6a333ac291710a238c5c668bf48e191deb4c1e629e3147b85660f16f5ca26')]:
    assert hashlib.sha256(pathlib.Path(path).read_bytes()).hexdigest()==digest
assert hashlib.sha256(p['authority']['intent']['content'].encode()).hexdigest()==p['authority']['intent']['sha256']
assert c.sha256([a])==p['authority']['anchors']['sha256']
assert p['diagnostic_plan'] is None and not a['fixtures']['pass'] and not a['fixtures']['fail']
save('request.json',p)
roles={'relevance':'relevant','compliance':'implemented','conflict':'violated','evidence':'evidenced'}
probes=[
 ('asserted','The stack discovery, batching and display implementation now supports stacks with more than 100 layers.','yes','yes','no','no','A claim of the required capacity is present, but no checkable artifact supports it.'),
 ('evidenced','Removed the former stack-size ceiling. tests/test_stack_capacity.py::test_150_layers passed and verifies discovery and output include every layer of a 150-layer local git fixture.','yes','yes','no','yes','150 exceeds 100; the named test supports the delivered capacity claim.'),
 ('silent','Refactored the stack pagination reader into a helper and preserved its behavior.','yes','no','no','no','Pagination is in scope; no supported capacity or conflict is described.'),
 ('topical','Changed scalability handling in the stack reader. The delivered account does not identify the supported layer count, so whether stacks above 100 layers work cannot be determined.','yes','unclear','no','no','A topic is mentioned without enough information to determine delivered compliance.'),
 ('conflict','Added a hard maximum of 100 stack layers. Larger stacks are rejected by the delivered discovery command.','yes','no','yes','no','Rejecting every stack above 100 directly conflicts with ANC-008.'),
 ('irrelevant','Updated the editor font preferences and terminal color-theme guide.','no','no','no','no','Editor preferences and color themes do not touch stack capacity.'),
 ('boundary','The discovery and display changes support a 101-layer stack; tests/test_capacity.py::test_101_layers passed and asserts all 101 layer records are returned and displayed.','yes','yes','no','yes','101 is beyond the 100-layer boundary and the test checks complete handling.'),
 ('quota-boundary','Stack traversal supports 150 layers; tests/test_capacity.py::test_150_layers passed. A GitHub-dependent operation may still fail when its required API budget is exhausted.','yes','yes','no','yes','Intent excludes zero-budget availability as a new requirement; it does not excuse a size cap.'),
 ('only-100','Validated stack discovery using tests/test_capacity.py::test_100_layers, which passes for exactly 100 layers. The report makes no claim or observation about any larger stack.','yes','no','no','no','A 100-layer test does not claim or evidence support above 100.'),
 ('truncated','Discovery accepts a 150-layer stack, but the delivered output deliberately drops every layer after the first 100.','yes','no','yes','no','Accepting an input while discarding all later layers does not support that stack.'),
 ('decorated','Delivery note: review and verification complete. The stack reader and output now support more than 100 layers. tests/test_capacity.py::test_150_layers passed, checking every layer is discovered and displayed. Documentation and review checklist were also completed.','yes','yes','no','yes','Extra reporting ceremony does not change the explicit capacity claim and supporting test.'),
]
cases=[]
for name,text,rel,imp,viol,evid,rationale in probes:
    expected=dict(zip(['relevant','implemented','violated','evidenced'],[rel,imp,viol,evid]))
    answers={k:{'type':'choice','choice':v,'confidence':1.0} for k,v in expected.items()}
    cases.append({'case_id':name,'state':{'anchor':{k:a[k] for k in ['id','statement','scope']},'item':{'id':name,'title':name,'text':text}},'expected':expected,'verdict':j.decide(answers,roles,0.0)[0],'rationale':'ANC-008 v1 and INTENT v2: '+rationale,'provenance':'Independent authority-derived synthetic probe; no approved fixtures supplied.'})
oracle={'frozen_before_live':True,'authority_sha256':c.sha256(p['authority']),'cases':cases}
save('frozen-oracle.json',oracle)
focus='The required behavior is support for stacks with more than 100 layers in sc-gh-stack.'
variants={
 'relevant':[
  'Does delivered work in `item.text` affect stack size limits, pagination, discovery, batching, or output handling? Judge overlap only. '+focus,
  'Is the delivered change within stack-capacity handling, including the discovery or presentation pipeline? Topic overlap counts even without a capacity claim. '+focus,
  'Would the reported work affect processing or displaying a stack beyond 100 layers, including pagination and size ceilings? Judge subject matter only. '+focus],
 'implemented':[
  'Does `item.text` state that delivered stack handling supports more than 100 layers? Judge the compliance claim only. Silence is no; vague scalability without a determinable capacity is unclear. Evidence is assessed separately.',
  'Does the delivered account claim stack operation beyond the 100-layer boundary? A successful 101-layer or 150-layer complete stack qualifies. Exactly 100 alone and future work do not qualify. Judge the claim, not its proof.',
  'Is above-100-layer support present in the described delivered behavior? Look for an explicit capacity statement or complete operation on a stack exceeding 100 layers. A known hard cap or truncation at 100 means no.'],
 'violated':[
  'Does the delivered behavior explicitly exclude stacks above 100 layers, or discard their layers because of a size cap? Judge conflict only. Silence about capacity and testing exactly 100 do not conflict.',
  'Does `item.text` describe an incompatible restriction such as rejection after 100 layers, one-page truncation, or output that drops later layers? No described incompatible behavior means no; absent claims are not violations.',
  'Is an explicit delivered decision inconsistent with supporting a stack exceeding 100 layers? Limits that reject larger stacks or truncate their records conflict. Missing evidence and API-budget failure alone do not establish a size violation.'],
 'evidenced':[
  'Does `item.text` cite a checkable artifact that supports its claim of stack support above 100 layers? A named test or command covering complete handling beyond 100, or a specific capacity diff, counts. Bare assertions and tests of exactly 100 do not.',
  'Is there concrete, checkable support for a delivered above-100-layer capacity claim? Judge supporting evidence only: test names, commands, paths or diffs must connect to the larger-stack behavior. Without such a claim answer no.',
  'Does the account link claimed handling of more than 100 stack layers to an identifiable verification or implementation artifact? A specific 101-plus fixture test counts. A topic mention, a bare success claim, or a 100-layer-only test does not.']}
criteria={
 'relevant':{'yes':'The work affects stack capacity, pagination, discovery, request batching, or output.','no':'The work is unrelated to those operations.','unclear':'The work is too vague to identify its subject.'},
 'implemented':{'yes':'The account claims delivered complete support beyond 100 layers, explicitly or through a larger-stack result.','no':'No such claim is made, the change is deferred, only exactly 100 is tested, or the described behavior rejects or truncates larger stacks.','unclear':'Scalability is mentioned but delivered above-100 support cannot be determined.'},
 'violated':{'yes':'Explicit delivered behavior rejects stacks above 100 or drops later layers because of a cap.','no':'No incompatible size restriction is described; silence, absent evidence and a test only at 100 do not conflict.','unclear':'A described size restriction is ambiguous about whether larger stacks are supported.'},
 'evidenced':{'yes':'An identifiable artifact supports a claim of complete stack handling beyond 100 layers.','no':'No above-100 compliance claim is made, or it has no supporting checkable artifact; exactly 100 does not evidence above-100 capacity.','unclear':'An artifact is mentioned but its support for the capacity claim cannot be determined.'}}
candidates=[{'candidate_id':'default','questions':p['current_questions']}]
for i in range(3): candidates.append({'candidate_id':f'capacity-{i+1}','questions':{role:{'type':'choice','instructions':variants[role][i],'criteria':criteria[role]} for role in variants}})
for cand in candidates: cand['digest']=c.sha256({'questions':cand['questions']})
save('frozen-candidates.json',candidates)
save('freeze.json',{'oracle_sha256':c.sha256(oracle),'candidates_sha256':c.sha256(candidates),'frozen_before_first_jev':True})
key=os.environ['TYPESAFE_API_KEY']; j.check_api_key(key)
records=[]; retry_count=0
def call(cand,case,rep):
    global retry_count
    rid=f"{p['correlation_id']}-{cand['candidate_id']}-{case['case_id']}-r{rep}"
    body={'model':'jev-latest','state':case['state'],'questions':cand['questions']}; save(rid+'.request.json',body)
    for attempt in range(2):
        try:
            raw=j.call_jev(body,key,40); save(rid+f'.attempt-{attempt+1}.raw.json',raw); j.validate_response(raw,cand['questions'])
            return {'run_id':rid,'candidate_id':cand['candidate_id'],'case_id':case['case_id'],'repeat':rep,'request_sha256':c.sha256(body),'encoded_request_sha256':hashlib.sha256(j.encode_body(body)).hexdigest(),'raw_response_sha256':c.sha256(raw),'response':raw}
        except j.JudgeError as exc:
            save(rid+f'.attempt-{attempt+1}.error.json',exc.to_json())
            if attempt or not exc.recoverable: raise
            retry_count+=1
with cf.ThreadPoolExecutor(max_workers=4) as pool:
    futures=[pool.submit(call,cand,case,rep) for cand in candidates for case in cases for rep in [1,2]]
    for f in cf.as_completed(futures): records.append(f.result())
records.sort(key=lambda x:x['run_id']); save('all-runs.json',records)
rankings=[]; tables={}
for cand in candidates:
    rows=[]; er=ev=st=reg=0; confs=[]
    for case in cases:
        runs=sorted([x for x in records if x['candidate_id']==cand['candidate_id'] and x['case_id']==case['case_id']],key=lambda x:x['repeat'])
        assert runs[0]['encoded_request_sha256']==runs[1]['encoded_request_sha256']
        choices=[{k:j.answer_choice(v)[0] for k,v in run['response']['answers'].items()} for run in runs]
        verdicts=[j.decide(run['response']['answers'],roles,0.0)[0] for run in runs]
        stable=choices[0]==choices[1]; st+=stable
        exact=sum(all(ch[k]==case['expected'][k] for ch in choices) for k in case['expected']); er+=exact
        ev+=all(v==case['verdict'] for v in verdicts); reg+=any(ch!=case['expected'] for ch in choices)
        confs.extend(min(j.answer_choice(run['response']['answers'][k])[1] for run in runs) for k in case['expected'])
        rows.append({'case_id':case['case_id'],'expected':case['expected'],'choices':choices,'expected_verdict':case['verdict'],'verdicts':verdicts,'stable':stable,'exact_role_cells':exact,'run_ids':[x['run_id'] for x in runs]})
    score={'exact_role_cells':er,'total_role_cells':len(cases)*4,'exact_semantic_verdicts':ev,'total_semantic_verdicts':len(cases),'stable_cases':st,'total_cases':len(cases),'regressions':reg}
    confs.sort(); diag={'threshold':.8,'cells_at_or_above_threshold':sum(x>=.8 for x in confs),'total_cells':len(confs),'minimum':min(confs),'p10':confs[int(.1*(len(confs)-1))],'median':statistics.median(confs),'mean':round(statistics.mean(confs),6)}
    accepted=er==len(cases)*4 and ev==st==len(cases) and reg==0
    rankings.append({'candidate_id':cand['candidate_id'],'accepted':accepted,'semantic_score':score,'confidence_diagnostics':diag,'complexity':len(c.canonical_bytes(cand['questions'])),'reason':'Accepted only for exact raw roles and threshold-zero verdicts, identical repeat choices, and zero regressions. Confidence is diagnostic.'}); tables[cand['candidate_id']]=rows
rankings.sort(key=lambda x:(not x['accepted'],-x['semantic_score']['exact_role_cells'],-x['semantic_score']['exact_semantic_verdicts'],-x['semantic_score']['stable_cases'],x['semantic_score']['regressions'],-x['confidence_diagnostics']['cells_at_or_above_threshold'],x['complexity'],x['candidate_id']))
best=rankings[0]; chosen=next(x for x in candidates if x['candidate_id']==best['candidate_id']); accepted=best['accepted']; score=best['semantic_score']; diag=best['confidence_diagnostics']; save('acceptance-table.json',tables)
hist=copy.deepcopy(p['tuning_history']); intent=p['authority']['intent']
event={'event_index':1,'previous_event_sha256':None,'event':'question_set_sealed' if accepted else 'question_set_rejected','protocol_version':p['tournament_protocol_version'],'authority':{'intent_id':intent['id'],'intent_version':intent['version'],'intent_sha256':intent['sha256'],'anchor_id':a['id'],'anchor_version':a['version'],'anchor_record_sha256':c.sha256(a)},'oracle':{'sha256':c.sha256(oracle),'case_ids':[x['case_id'] for x in cases],'case_count':len(cases),'repeat_count':2},'candidate':{'candidate_id':chosen['candidate_id'],'question_sha256':chosen['digest']},'evidence':{'canonical_request_sha256':[x['request_sha256'] for x in records],'raw_response_sha256':[x['raw_response_sha256'] for x in records],'run_ids':[x['run_id'] for x in records]},'score':dict(score,confidence=diag),'decision':{'status':'sealed' if accepted else 'rejected','question_set_sha256':chosen['digest'] if accepted else None,'reason_code':'TOURNAMENT.EXACT' if accepted else 'TOURNAMENT.SEMANTIC_REJECTED'},'supersedes':None}
hist['events'].append(event)
data={'operation':'tune','gate':'development','accepted':accepted,'tournament_protocol_version':p['tournament_protocol_version'],'production_confidence_threshold':p['production_confidence_threshold'],'confidence_reference_threshold':.8,'semantic_score':score,'confidence_diagnostics':diag,'tuning_history_before_sha256':c.sha256(p['tuning_history']),'tuning_history_after':hist,'tuning_history_after_sha256':c.sha256(hist),'production_semantics_unchanged':True,'authority_citations':['ANC-008 v1','INTENT v2'],'oracle_sha256':c.sha256(oracle),'sealed_question_set':{'digest':chosen['digest'],'questions':chosen['questions']} if accepted else None,'candidate_rankings':rankings,'acceptance_table':tables[chosen['candidate_id']],'evidence':{'directory':str(BASE),'all_runs':'all-runs.json','frozen_oracle':'frozen-oracle.json','frozen_candidates':'frozen-candidates.json','repeat_requests_byte_identical':True,'round_count':1,'raw_responses_preserved':True},'explanation':'Independent authority-derived oracle frozen before live calls. Three materially distinct anchor-specific bundles and current defaults evaluated over identical probes. No implementation, development reports, or gate results inspected. Empty approved fixture arrays preserved. Production confidence threshold remains unchanged.','planner_action':'Use the sealed set only if accepted; retain all rejected evidence.','question_action':None,'sealed_question_set_digest_before':None,'sealed_question_set_digest_after':chosen['digest'] if accepted else None,'authority_recommendations':[]}
result={'schema_version':'1.0.0','success':True,'canceled':False,'aborted_by':None,'data':data,'error':None,'metadata':{'duration_ms':int((time.monotonic()-start)*1000),'tool_calls':len(records)+retry_count,'retry_count':retry_count,'correlation_id':p['correlation_id'],'jev_run_ids':[x['run_id'] for x in records],'planner_observation_trust':None,'authoritative_sources_unchanged':True}}
jsonschema.validate(result,json.loads((SK/'assets/schemas/anchor-tuning-result.schema.json').read_text())); c.validate_result(result)
save('result.json',result); save('result-vars.json',{k:v for k,v in result.items() if k!='schema_version'})
subprocess.run(['sc-compose','render','--file',str(SK/'templates/anchor-tuning-result.md.j2'),'--root',str(PLUGIN),'--var-file',str(BASE/'result-vars.json'),'--strict','--check-render','--output',str(BASE/'response.md')],check=True)
rendered=json.loads(re.findall(r'```json\s*\n(.*?)\n```',(BASE/'response.md').read_text(),re.S)[0]); assert rendered==result
jsonschema.validate(rendered,json.loads((SK/'assets/schemas/anchor-tuning-result.schema.json').read_text())); c.validate_result(rendered)
save('validation.json',{'request_schema':True,'request_relational':True,'runtime_and_authority_digests':True,'result_schema':True,'result_relational':True,'strict_template_render':True,'rendered_round_trip':True})
print(json.dumps({'accepted':accepted,'rankings':rankings,'response':str(BASE/'response.md')}))
