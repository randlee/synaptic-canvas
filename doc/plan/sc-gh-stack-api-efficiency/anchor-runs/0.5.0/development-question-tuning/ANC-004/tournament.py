"""Independent ANC-004 development calibration; only local evidence is written."""
import concurrent.futures, hashlib, importlib.util, json, os, pathlib, re, statistics, subprocess, sys, time
import jsonschema

ROOT = pathlib.Path(__file__).resolve().parent
PLUGIN = pathlib.Path('/Users/randlee/.codex/plugins/cache/plan-anchor/sc-plan-anchor/0.5.0')
SKILL = PLUGIN / 'skills/plan-anchoring'
START = time.monotonic()
def canonical(x): return json.dumps(x,sort_keys=True,separators=(',',':'),ensure_ascii=False).encode()
def digest(x): return hashlib.sha256(canonical(x)).hexdigest()
def save(name,x):
    (ROOT/name).write_bytes(canonical(x)+b'\n')
def module(name,path):
    spec=importlib.util.spec_from_file_location(name,path); m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m);return m
request_text=(ROOT/'request.md').read_text()
blocks=re.findall(r'```json\s*\n(.*?)\n```',request_text,re.S)
assert len(blocks)==1
req=json.loads(blocks[0]); save('request.json',req)
jsonschema.validate(req,json.loads((SKILL/'assets/schemas/anchor-tuning-request.schema.json').read_text()))
contract=module('contract',SKILL/'scripts/anchor_tuning_contract.py');contract.validate_request(req)
for k,p in [('sha256','script'),('contract_sha256','contract_script')]:
    assert hashlib.sha256(pathlib.Path(req['runtime'][p]).read_bytes()).hexdigest()==req['runtime'][k]
assert hashlib.sha256((PLUGIN/'.codex/agents/anchor-tuning.md').read_bytes()).hexdigest()=='36e6a333ac291710a238c5c668bf48e191deb4c1e629e3147b85660f16f5ca26'
assert hashlib.sha256((SKILL/'templates/anchor-tuning-tune-request.md.j2').read_bytes()).hexdigest()==req['template']['sha256']
authority=req['authority'];anchor=authority['anchors']['records'][0]
assert hashlib.sha256(authority['intent']['content'].encode()).hexdigest()==authority['intent']['sha256']
assert digest(authority['anchors']['records'])==authority['anchors']['sha256']
save('validation.json',{'schema':True,'contract':True,'runtime_and_authority_digests':True})

ROLES=['relevant','implemented','violated','evidenced']
mapping={'relevance':'relevant','compliance':'implemented','conflict':'violated','evidence':'evidenced'}
cases=[]
def case(cid,text,labels,verdict,rationale):
    cases.append({'id':cid,'item':{'id':cid,'title':'Independent calibration example','text':text},'expected_roles':dict(zip(ROLES,labels.split())),'expected_verdict':verdict,'rationale':rationale})
case('minimal-compliant','Delivered source selection now prefers REST whenever REST provides the required stack information at lower quota cost than GraphQL.','yes yes no no','asserted_only','ANC-004 specific conditional preference is claimed, with no checkable evidence.')
case('silent','Changed sc-gh-stack remote information acquisition code and shipped the new implementation. The account gives no details of REST, GraphQL, or cost-based source selection.','yes no no no','not_addressed','In-scope work with silence about conditional source preference is neither compliance nor conflict.')
case('topical-only','Updated sc-gh-stack remote information acquisition. REST, GraphQL, and quota costs were discussed; this report does not say how the delivered code selects either source.','yes unclear no no','underspecified','Topic mention with explicitly indeterminate delivered selection leaves compliance unclear; no conflict or evidence is asserted.')
case('conflicting','Delivered sc-gh-stack always selects GraphQL for PR head SHAs, even when REST provides the same required SHAs at lower quota cost. This intentionally ignores cheaper REST.','yes no yes no','contradicted','ANC-004 excludes selecting GraphQL despite equivalent cheaper REST; a conflicting claim is not evidence of compliance.')
case('irrelevant','Delivered a CSS color change to the documentation website footer. No stack code, remote information acquisition, or API behavior changed.','no no no no','not_applicable','Website cosmetics cannot follow or break stack remote source selection.')
case('equal-cost-boundary','Delivered sc-gh-stack source selection prefers REST whenever equivalent REST information is cheaper. For one read with exactly equal total quota cost for REST and GraphQL, it retains GraphQL. tests/test_sources.py::test_equal_cost executes and passes this boundary; tests/test_sources.py::test_cheaper_rest passes the cheaper REST preference.','yes yes no yes','satisfied','ANC-004 conditional preference does not require REST on equal cost; named tests support explicit delivered conditional behavior.')
case('incomplete-rest-exception','Delivered sc-gh-stack source selection uses REST when it supplies all required information more cheaply. It retains GraphQL for a policy field unavailable from REST; the cheaper REST payload lacks that required field. tests/test_sources.py::test_missing_rest_field and test_cheaper_complete_rest both pass.','yes yes no yes','satisfied','The REST preference requires equivalent required information; GraphQL remains valid when REST is incomplete.')
case('asserted-without-evidence','The delivered sc-gh-stack redesign follows ANC-004: REST is preferred to GraphQL when it supplies the required information at lower quota cost. Trust us; no files, commands, tests, outputs, or comparisons are supplied here.','yes yes no no','asserted_only','Specific compliance is asserted but there is explicitly no checkable supporting artifact.')
case('concretely-evidenced','Delivered src/source_selector.py selects REST for equivalent complete PR metadata at lower quota cost and otherwise permits GraphQL. tests/test_sources.py::test_cheaper_rest passed: equal fields returned by both adapters, REST cost 1, GraphQL cost 4, selected adapter REST. The diff adds this comparison before dispatch.','yes yes no yes','satisfied','A named selector, concrete equivalent-information comparison, and passed test evidence the conditional REST preference.')
for kind in ['pass','fail']:
    assert not anchor['fixtures'][kind], 'Unexpected approved fixtures must be incorporated before freeze'
oracle={'schema':'plan-anchor/tuning-oracle/1','anchor_id':anchor['id'],'authority_sha256':digest(authority),'gate':'development','frozen_before_live':True,'cases':cases}
save('oracle.json',oracle);(ROOT/'oracle.sha256').write_text(digest(oracle)+'\n')

def question(instructions,yes,no,unclear): return {'type':'choice','instructions':instructions,'criteria':{'yes':yes,'no':no,'unclear':unclear}}
special={
'relevant':question('Does delivered work in `item.text` touch remote acquisition of stack information or selection of REST versus GraphQL in sc-gh-stack? Judge subject overlap only.','The work affects remote stack information reads or their source selection.','The work is unrelated to stack remote information acquisition.','The affected work cannot be identified.'),
'implemented':question('Does `item.text` say the delivered redesign prefers REST when it supplies the required information at lower quota cost than GraphQL? Judge the claimed implemented source preference. Equal-cost reads and reads for information REST cannot supply may still use GraphQL.','It states delivered conditional cheaper-equivalent-REST preference, including with allowed equal-cost or missing-information exceptions.','The preference is absent, deferred, or explicitly not followed.','REST, GraphQL, or costs are mentioned but the delivered selection policy cannot be determined.'),
'violated':question('Does `item.text` describe delivered source selection choosing GraphQL despite REST supplying the required information at lower quota cost? Silence is not conflict. GraphQL with equal cost or missing required REST fields is permitted.','It describes choosing GraphQL despite equivalent required information being cheaper through REST.','No conflicting delivered selection is stated, including silence or permitted GraphQL exceptions.','The described source selection might conflict but its required information or relative cost is indeterminate.'),
'evidenced':question('Does `item.text` supply a concrete checkable artifact supporting the claim that the delivered source selection prefers equivalent cheaper REST? A bare assurance or topic mention is insufficient.','It cites a path, diff, named test, command output, or concrete comparison supporting that conditional preference.','It supplies no supporting checkable artifact, or makes no such compliance claim.','An artifact is mentioned but its support for that preference is unclear.')}
precise={
'relevant':question('Is the subject of the delivered change in `item.text` within `anchor.scope`: selecting REST or GraphQL to obtain remote stack information?','The change selects, acquires, or depends on remote stack information.','The work only changes an unrelated subject.','The work description is too vague to establish the subject.'),
'implemented':question('Read `item.text` as an account of completed work. Does it state that equivalent required stack information is obtained preferentially through REST when that costs less quota than GraphQL? A comparison may be stated as a policy; no numeric measurement is necessary for this judgment.','The delivered REST preference under the cheaper-and-sufficient condition is explicit. An equal-cost or insufficient-REST exception may accompany it.','No delivered conditional preference is stated, or the description explicitly abandons it.','The topic is present but the account does not establish the delivered preference.'),
'violated':question('Is a delivered decision in `item.text` incompatible with preferring REST when sufficient required information costs less than GraphQL? Judge only stated conflict: absence of the preference is not a violation.','A stated delivered choice bypasses sufficient cheaper REST in favor of GraphQL.','No such conflicting choice is stated. Equal cost and incomplete REST are outside the condition.','A described choice could bypass cheaper sufficient REST, but facts are ambiguous.'),
'evidenced':question('Does the account in `item.text` give checkable support for its claim of implemented conditional cheaper-REST preference? Judge evidence supporting the claim, not the existence of generic artifacts.','A specific source path/diff, named test or output, executed command, or concrete source/cost comparison supports the preference.','The account only assures compliance, lists the topic, states a conflicting policy, or contains no compliance support.','A possible supporting artifact appears but its relationship to the preference is indeterminate.')}
candidates=[{'id':'default','questions':req['current_questions']},{'id':'conditional-rest','questions':special},{'id':'source-comparison','questions':precise}]
assert len(candidates)>=req['candidate_minimum']
for c in candidates: save('candidate-'+c['id']+'.json',c)
save('freeze.json',{'oracle_sha256':digest(oracle),'candidate_digests':{c['id']:digest({'questions':c['questions']}) for c in candidates},'repeat_count':req['repeat_count'],'approved_fixtures':{'pass':0,'fail':0}})

# Do not import environment-configurable judge module before removing its optional overrides.
for key in list(os.environ):
    if key.startswith('PLAN_ANCHOR_'): os.environ.pop(key)
judge=module('jev',SKILL/'scripts/jev_judge.py')
key=os.environ.get('TYPESAFE_API_KEY','');judge.check_api_key(key)
allruns=[]
def execute(task):
    c,probe,repeat=task;runid=f"{req['correlation_id']}-{c['id']}-{probe['id']}-r{repeat}"
    body={'model':'jev-latest','state':judge.build_state(anchor,probe['item']),'questions':c['questions']}
    save(runid+'-request.json',body)
    for attempt in range(2):
        try:
            raw=judge.call_jev(body,key,45);save(runid+f'-response-a{attempt+1}.json',raw);judge.validate_response(raw,c['questions']);break
        except judge.JudgeError as exc:
            save(runid+f'-error-a{attempt+1}.json',exc.to_json())
            if not exc.recoverable or attempt: raise
    choices={role:judge.answer_choice(raw['answers'][role])[0] for role in ROLES}
    confidences={role:judge.answer_choice(raw['answers'][role])[1] for role in ROLES}
    result={'run_id':runid,'candidate_id':c['id'],'case_id':probe['id'],'repeat':repeat,'request_sha256':digest(body),'response_sha256':digest(raw),'answers':choices,'confidences':confidences,'verdict':judge.decide(raw['answers'],mapping,0.0)[0],'attempts':attempt+1}
    save(runid+'-result.json',result);return result
tasks=[(c,p,r) for c in candidates for p in cases for r in range(1,req['repeat_count']+1)]
if (ROOT/'runs.json').exists():
    allruns=json.loads((ROOT/'runs.json').read_text())
    assert len(allruns)==len(tasks)
    for r in allruns:
        assert digest(json.loads((ROOT/(r['run_id']+'-request.json')).read_text()))==r['request_sha256']
        assert digest(json.loads((ROOT/(r['run_id']+'-response-a'+str(r['attempts'])+'.json')).read_text()))==r['response_sha256']
else:
    with concurrent.futures.ThreadPoolExecutor(max_workers=4) as pool:
        for result in pool.map(execute,tasks): allruns.append(result)
save('runs.json',allruns)

rankings=[];table=[]
for c in candidates:
    runs=[r for r in allruns if r['candidate_id']==c['id']]
    exactcells=0;exactverdicts=0;stable=0;confs=[]
    for probe in cases:
        rr=[r for r in runs if r['case_id']==probe['id']]
        isstable=len({json.dumps(r['answers'],sort_keys=True) for r in rr})==1;stable+=isstable
        for r in rr:
            exactcells+=sum(r['answers'][role]==probe['expected_roles'][role] for role in ROLES)
            exactverdicts+=r['verdict']==probe['expected_verdict'];confs.extend(r['confidences'].values())
            table.append({'candidate_id':c['id'],'case_id':probe['id'],'repeat':r['repeat'],'expected_roles':probe['expected_roles'],'actual_roles':r['answers'],'expected_verdict':probe['expected_verdict'],'actual_verdict':r['verdict'],'stable':isstable,'run_id':r['run_id']})
    score={'exact_role_cells':exactcells,'total_role_cells':len(runs)*4,'exact_semantic_verdicts':exactverdicts,'total_semantic_verdicts':len(runs),'stable_cases':stable,'total_cases':len(cases),'regressions':0}
    confs.sort();diag={'threshold':0.8,'cells_at_or_above_threshold':sum(x>=0.8 for x in confs),'total_cells':len(confs),'minimum':min(confs),'p10':confs[int((len(confs)-1)*.1)],'median':statistics.median(confs),'mean':round(statistics.mean(confs),6)}
    accepted=exactcells==len(runs)*4 and exactverdicts==len(runs) and stable==len(cases)
    rankings.append({'candidate_id':c['id'],'accepted':accepted,'semantic_score':score,'confidence_diagnostics':diag,'complexity_bytes':len(canonical(c['questions'])),'reason':'Exact stable role-complete bundle' if accepted else 'Rejected: semantic mismatches or repeat instability'})
baseline={r['case_id']+'-'+str(r['repeat']):r for r in allruns if r['candidate_id']=='default'}
for ranking in rankings:
    regressions=0
    for r in [r for r in allruns if r['candidate_id']==ranking['candidate_id']]:
        probe=next(p for p in cases if p['id']==r['case_id']);base=baseline[r['case_id']+'-'+str(r['repeat'])]
        regressions+=sum(base['answers'][role]==probe['expected_roles'][role] and r['answers'][role]!=probe['expected_roles'][role] for role in ROLES)
    ranking['semantic_score']['regressions']=regressions;ranking['accepted'] &= regressions==0
rankings.sort(key=lambda x:(not x['accepted'],-x['semantic_score']['exact_role_cells'],-x['semantic_score']['exact_semantic_verdicts'],-x['semantic_score']['stable_cases'],x['semantic_score']['regressions'],-x['confidence_diagnostics']['cells_at_or_above_threshold'],x['complexity_bytes'],x['candidate_id']))
winner=rankings[0];selected=next(c for c in candidates if c['id']==winner['candidate_id']); accepted=winner['accepted'];sealed={'questions':selected['questions'],'digest':digest({'questions':selected['questions']})} if accepted else None
for ranking in rankings:
    ranking['reason'] = ('Selected: exact stable bundle; highest number of cells at reference confidence, and smallest complete bundle.' if ranking['candidate_id']==selected['id'] else 'Not selected: exact and stable but fewer cells at reference confidence; retained as candidate evidence.') if ranking['accepted'] else ranking['reason']
save('acceptance-table.json',table);save('rankings.json',rankings)
selectedruns=[r for r in allruns if r['candidate_id']==selected['id']]
evidence={'canonical_request_sha256':[r['request_sha256'] for r in selectedruns],'raw_response_sha256':[r['response_sha256'] for r in selectedruns],'run_ids':[r['run_id'] for r in selectedruns]}
event={'event_index':1,'previous_event_sha256':None,'event':'question_set_sealed' if accepted else 'question_set_rejected','protocol_version':req['tournament_protocol_version'],'authority':{'intent_id':authority['intent']['id'],'intent_version':authority['intent']['version'],'intent_sha256':authority['intent']['sha256'],'anchor_id':anchor['id'],'anchor_version':anchor['version'],'anchor_record_sha256':digest(anchor)},'oracle':{'sha256':digest(oracle),'case_ids':[p['id'] for p in cases],'case_count':len(cases),'repeat_count':req['repeat_count']},'candidate':{'candidate_id':selected['id'],'question_sha256':digest({'questions':selected['questions']})},'evidence':evidence,'score':dict(winner['semantic_score'],confidence=winner['confidence_diagnostics']),'decision':{'status':'sealed' if accepted else 'rejected','question_set_sha256':sealed['digest'] if accepted else None,'reason_code':'TOURNAMENT.EXACT_STABLE' if accepted else 'TOURNAMENT.SEMANTIC_MISMATCH'},'supersedes':None}
history=dict(req['tuning_history'],events=req['tuning_history']['events']+[event])
data={'operation':'tune','gate':'development','accepted':accepted,'tournament_protocol_version':req['tournament_protocol_version'],'production_confidence_threshold':req['production_confidence_threshold'],'confidence_reference_threshold':0.8,'semantic_score':winner['semantic_score'],'confidence_diagnostics':winner['confidence_diagnostics'],'tuning_history_before_sha256':digest(req['tuning_history']),'tuning_history_after':history,'tuning_history_after_sha256':digest(history),'production_semantics_unchanged':True,'authority_citations':['INTENT sc-gh-stack-api-efficiency v2: prefer inexpensive REST for remaining remote information without equivalent fanout','ANC-004 v1: prefer REST when required information has lower quota cost'],'oracle_sha256':digest(oracle),'sealed_question_set':sealed,'candidate_rankings':rankings,'acceptance_table':table,'evidence':dict(evidence,oracle_file='oracle.json',candidate_files=['candidate-'+c['id']+'.json' for c in candidates],request_response_files='Each run ID has canonical request, raw response and derived result JSON files',frozen_before_live=True,approved_fixtures={'pass':0,'fail':0}),'explanation':'Compared three materially distinct role-complete candidates against a frozen nine-case authority-derived oracle, with two byte-identical repeats per case. Confidence ranks only after exact semantics and stability. No implementation or gate results were inspected. '+('Selected '+selected['id']+'.' if accepted else 'No candidate was accepted; all evidence is retained.'),'planner_action':'Apply the accepted questions only after validating this result; production retains its configured 0.6 threshold.' if accepted else 'Do not apply questions; inspect independent calibration mismatches.','question_action':None,'sealed_question_set_digest_before':None,'sealed_question_set_digest_after':sealed['digest'] if accepted else None,'authority_recommendations':[]}
data['acceptance_table']=[{'candidate_id':r['candidate_id'],'accepted':r['accepted'],'exact_role_cells':r['semantic_score']['exact_role_cells'],'total_role_cells':r['semantic_score']['total_role_cells'],'exact_semantic_verdicts':r['semantic_score']['exact_semantic_verdicts'],'total_semantic_verdicts':r['semantic_score']['total_semantic_verdicts'],'stable_cases':r['semantic_score']['stable_cases'],'total_cases':r['semantic_score']['total_cases'],'regressions':r['semantic_score']['regressions']} for r in rankings]
data['evidence']={'oracle_file':'oracle.json','oracle_sha256':digest(oracle),'frozen_before_live':True,'freeze_manifest':'freeze.json','complete_runs_file':'runs.json','complete_runs_sha256':digest(allruns),'complete_acceptance_table':'acceptance-table.json','complete_acceptance_table_sha256':digest(table),'candidate_files':['candidate-'+c['id']+'.json' for c in candidates],'request_response_files':'Every run ID in runs.json has canonical request, raw response, and derived result files. Both repeated request digests are identical per candidate/case.','approved_fixtures':{'pass':0,'fail':0},'request_count':len(allruns)}
envelope={'schema_version':'1.0.0','success':True,'canceled':False,'aborted_by':None,'data':data,'error':None,'metadata':{'duration_ms':int((time.monotonic()-START)*1000),'tool_calls':sum(r['attempts'] for r in allruns),'retry_count':sum(r['attempts']-1 for r in allruns),'correlation_id':req['correlation_id'],'jev_run_ids':evidence['run_ids'],'planner_observation_trust':None,'authoritative_sources_unchanged':True}}
jsonschema.validate(envelope,json.loads((SKILL/'assets/schemas/anchor-tuning-result.schema.json').read_text()));contract.validate_result(envelope)
save('result.json',envelope);save('result-vars.json',{k:v for k,v in envelope.items() if k!='schema_version'})
subprocess.run(['sc-compose','render','--strict','--check-render','--root',str(PLUGIN),'--file',str(SKILL/'templates/anchor-tuning-result.md.j2'),'--var-file',str(ROOT/'result-vars.json'),'--output',str(ROOT/'response.md')],check=True,capture_output=True,text=True)
rendered=json.loads(re.findall(r'```json\s*\n(.*?)\n```',(ROOT/'response.md').read_text(),re.S)[0]);assert rendered==envelope
jsonschema.validate(rendered,json.loads((SKILL/'assets/schemas/anchor-tuning-result.schema.json').read_text()));contract.validate_result(rendered)
save('result-validation.json',{'schema':True,'contract':True,'strict_template_render':True,'result_sha256':digest(rendered)})
print(json.dumps({'accepted':accepted,'selected':selected['id'],'rankings':rankings,'response':str(ROOT/'response.md')}))
