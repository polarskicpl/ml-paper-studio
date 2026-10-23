"""Synthetic CLI boundary tests; no research results or real PDF build is claimed."""
import copy
import importlib.util
import json
import pathlib
import shutil
import subprocess
import sys
import tempfile

sys.dont_write_bytecode=True
SCRIPT=pathlib.Path(__file__).resolve().parents[1]/'skills/ml-paper-studio/scripts/paper_workspace.py'
compile(SCRIPT.read_text(),str(SCRIPT),'exec')
spec=importlib.util.spec_from_file_location('draft_workspace',SCRIPT)
p=importlib.util.module_from_spec(spec);spec.loader.exec_module(p)
root=pathlib.Path(tempfile.mkdtemp(prefix='ml-paper-studio-draft-regression-'))
base=root/'base';base.mkdir()
results=[]

def write(w,path,value):
    target=w/path;target.parent.mkdir(parents=True,exist_ok=True)
    target.write_text(json.dumps(value,ensure_ascii=False),encoding='utf-8')

def read(w,path):return json.loads((w/path).read_text(encoding='utf-8'))
def put(w,role,value):write(w,p.PATHS[role],value)
def mutate(w,path,action):
    value=read(w,path);action(value);write(w,path,value)

def call(w,*args):
    result=subprocess.run([sys.executable,str(SCRIPT),*args,'--workspace',str(w)],capture_output=True,text=True)
    assert 'Traceback' not in result.stderr,result.stderr
    return result.returncode,json.loads(result.stdout or result.stderr)

def check(w,stage=3,expected=0,code=None,purpose='draft'):
    args=['check','--stage',str(stage)]
    if purpose is not None:args+=['--purpose',purpose]
    status,report=call(w,*args)
    assert status==expected,(status,report)
    if code:assert any(row['code']==code for row in report.get('findings',[])),report
    if purpose=='draft' and status!=2:
        assert report['schema']=='ml-paper-studio.draft-check/1',report
        assert report['submission_readiness']=='not_assessed',report
        assert report['drafting']['authorization_authenticated'] is False
    return report

def case(name,action):
    w=root/name;shutil.copytree(base,w,symlinks=True)
    try:action(w);results.append({'case':name,'status':'pass'})
    except Exception as exc:
        results.append({'case':name,'status':'fail','error':str(exc)})
        raise

assert call(base,'init','--project-root',str(root),'--paper-id','synthetic-draft')[0]==0
state=read(base,'paper-state.json')
state['drafting']={'mode':'parallel','declaration_path':'evidence/draft-declaration.json'}
write(base,'paper-state.json',state)
for role in ['chinese','english']:
    path=base/p.PATHS[role];path.parent.mkdir(parents=True,exist_ok=True)
    path.write_text('Internal synthetic fixture. Results: [[RESULT:R1]]\n',encoding='utf-8')
(base/'evidence').mkdir(exist_ok=True)
(base/'evidence/source.py').write_text('Synthetic method fixture only.\n')
put(base,'evidence',{'schema':'ml-paper-studio.evidence/1',
    'records':[{'id':'EV1','root':'workspace','path':'evidence/source.py',
        'sha256':p.digest(base/'evidence/source.py'),'locator':'line 1','kind':'code',
        'status':'observed','conditions':{},'interpretation':'Synthetic implementation fixture only.'}],
    'claims':[{'id':'C1','text':'A candidate empirical finding; no result is asserted.',
        'claim_type':'empirical','evidence_ids':['EV1'],'source_ids':[],
        'status':'unresolved','use_in_manuscript':True,'scope':'Synthetic pending fixture only.'}]})
write(base,'evidence/draft-declaration.json',{'schema':'ml-paper-studio.draft-declaration/1',
    'authorization':{'user_message_ref':'synthetic-fixture-message','quote':'Synthetic permission to prepare an internal discussion draft.','scope':'Internal discussion; no submission.'},
    'pending':[{'id':'R1','claim_id':'C1','locations':['Results'],
        'required_evidence':'Real evaluation output under the declared protocol.',
        'status':'pending','placeholder':'[[RESULT:R1]]'}]})
put(base,'translation',{'schema':'ml-paper-studio.translation/1',
    'source_sha256':p.digest(base/p.PATHS['chinese']),'target_sha256':p.digest(base/p.PATHS['english']),
    'checks':{key:{'status':'pass','evidence':'Synthetic fidelity fixture; not a real translation review.'}
        for key in ['numbers','formulas','citation_attachment','claim_strength','terminology']},'entries':[]})
(base/'paper').mkdir();(base/'paper/main.tex').write_text('Synthetic source [[RESULT:R1]]\n')
(base/'paper/settings.cfg').write_text('Synthetic input.\n')
(base/'paper/paper.pdf').write_bytes(b'%PDF-synthetic-boundary-fixture-only\n')
put(base,'build',{'schema':'ml-paper-studio.build/1','status':'success','engine':'synthetic-fixture',
    'command_or_tool':'No real build; synthetic record for byte-binding tests only.',
    'built_at':'synthetic-fixture','source_manifest':p.paper_inputs(base),
    'pdf_path':'paper/paper.pdf','pdf_sha256':p.digest(base/'paper/paper.pdf'),'diagnostics':[]})

def default_strict_unchanged(w):
    default=check(w,expected=1,purpose=None)
    explicit=check(w,expected=1,purpose='strict')
    for report in [default,explicit]:
        report.pop('checked_at');assert report['schema']=='ml-paper-studio.workspace-check/1'
    assert default==explicit
    assert any(row['code']=='open_core_claim' for row in default['findings'])
case('default_strict_matches_explicit_strict',default_strict_unchanged)
case('authorized_pending_chinese_without_confirmation_or_review',lambda w:check(w))
case('authorized_pending_translation',lambda w:check(w,4))
def internal_pdf(w):
    report=check(w,5)
    assert 'pdf_visual_and_submission_review' in report['not_assessed']
    assert not (w/p.PATHS['venue']).exists() and not (w/p.PATHS['pdf_check']).exists()
    assert report['drafting']['pending'][0]['status']=='pending'
case('internal_pdf_without_venue_or_visual_claim',internal_pdf)
case('strict_pdf_still_requires_venue',lambda w:check(w,5,1,'venue_unverified',purpose='strict'))
for stage in [0,1,2]:
    case('draft_stage_'+str(stage)+'_structured_rejection',lambda w,stage=stage:check(w,stage,2))

def declaration_change(w,action):mutate(w,'evidence/draft-declaration.json',action)
def evidence_change(w,action):mutate(w,p.PATHS['evidence'],action)
case('missing_actual_authorization',lambda w:(declaration_change(w,lambda d:d['authorization'].update(quote=' ')),check(w,expected=2)))
case('wrong_declaration_shape',lambda w:(write(w,'evidence/draft-declaration.json',[]),check(w,expected=2)))
case('wrong_pending_shape',lambda w:(declaration_change(w,lambda d:d.update(pending=[None])),check(w,expected=2)))
case('missing_locations',lambda w:(declaration_change(w,lambda d:d['pending'][0].update(locations=[])),check(w,expected=2)))
case('missing_required_evidence',lambda w:(declaration_change(w,lambda d:d['pending'][0].update(required_evidence=' ')),check(w,expected=2)))
case('wrong_drafting_shape',lambda w:(mutate(w,'paper-state.json',lambda d:d.update(drafting=[])),check(w,expected=2)))
case('unknown_draft_claim',lambda w:(declaration_change(w,lambda d:d['pending'][0].update(claim_id='C404')),check(w,expected=1,code='unknown_draft_claim')))
case('duplicate_draft_id',lambda w:(declaration_change(w,lambda d:d['pending'].append(copy.deepcopy(d['pending'][0]))),check(w,expected=1,code='duplicate_draft_id')))
case('duplicate_pending_claim',lambda w:(declaration_change(w,lambda d:d['pending'].append(dict(d['pending'][0],id='R2',placeholder='[[RESULT:R2]]'))),check(w,expected=1,code='duplicate_pending_claim')))
case('unregistered_unresolved_claim',lambda w:(declaration_change(w,lambda d:d.update(pending=[])),check(w,expected=1,code='unregistered_draft_claim')))
case('contradicted_claim_never_assumed',lambda w:(evidence_change(w,lambda d:d['claims'][0].update(status='contradicted')),check(w,expected=1,code='draft_contradicted_claim')))
def invented_result(w,status):
    evidence_change(w,lambda d:(d['records'][0].update(kind='result',status=status),d['claims'][0].update(status='supported')))
    check(w,expected=1,code='nonobserved_result')
for status in ['planned','synthetic']:
    case(status+'_cannot_be_supported_by_declaration',lambda w,status=status:invented_result(w,status))
case('changed_observed_evidence_not_waived',lambda w:((w/'evidence/source.py').write_text('Changed.'),check(w,expected=1,code='changed_evidence')))
case('missing_evidence_id',lambda w:(evidence_change(w,lambda d:d['claims'][0].update(evidence_ids=['EV404'])),check(w,expected=1,code='missing_evidence_id')))
def missing_source(w):
    evidence_change(w,lambda d:d['claims'][0].update(source_ids=['S404']))
    put(w,'sources',{'schema':'ml-paper-studio.sources/1','entries':[]})
    check(w,expected=1,code='missing_source_id')
case('missing_source_id',missing_source)
case('resolved_not_a_status_waiver',lambda w:(declaration_change(w,lambda d:d['pending'][0].update(status='resolved')),check(w,expected=1,code='unresolved_ledger_resolution')))
case('dropped_claim_still_in_scope',lambda w:(declaration_change(w,lambda d:d['pending'][0].update(status='dropped')),check(w,expected=1,code='dropped_claim_in_scope')))
case('missing_chinese_placeholder',lambda w:((w/p.PATHS['chinese']).write_text('No placeholder.'),check(w,expected=1,code='missing_draft_placeholder')))
def missing_english(w):
    (w/p.PATHS['english']).write_text('No placeholder.')
    mutate(w,p.PATHS['translation'],lambda d:d.update(target_sha256=p.digest(w/p.PATHS['english'])))
    check(w,4,1,'missing_draft_placeholder')
case('missing_english_placeholder_even_with_fidelity_record',missing_english)
case('orphan_placeholder',lambda w:((w/p.PATHS['chinese']).write_text('[[RESULT:R1]] [[RESULT:R404]]'),check(w,expected=1,code='orphan_draft_placeholder')))
case('changed_translation_requires_review',lambda w:((w/p.PATHS['english']).write_text('Changed [[RESULT:R1]]'),check(w,4,1,'stale_translation_check')))
case('unchanged_translation_unreviewed_semantics_rejected',lambda w:(mutate(w,p.PATHS['translation'],lambda d:d['checks']['claim_strength'].update(status='not_run')),check(w,4,1,'translation_not_checked')))
case('draft_pdf_missing',lambda w:((w/'paper/paper.pdf').unlink(),check(w,5,1,'pdf_missing')))
case('draft_pdf_bytes_changed',lambda w:((w/'paper/paper.pdf').write_bytes(b'%PDF-changed'),check(w,5,1,'pdf_binding')))
case('draft_pdf_inputs_changed',lambda w:((w/'paper/settings.cfg').write_text('Changed.'),check(w,5,1,'stale_pdf_inputs')))
def no_mutation(w):
    before={str(path.relative_to(w)):path.read_bytes() for path in w.rglob('*') if path.is_file()}
    for stage in [3,4,5]:check(w,stage)
    after={str(path.relative_to(w)):path.read_bytes() for path in w.rglob('*') if path.is_file()}
    assert before==after
case('draft_checks_never_modify_state_evidence_or_authorization',no_mutation)

report={'scope':'Synthetic local CLI interface and byte-binding fixtures only; no network, real research result, user authorization or PDF compilation claimed.',
    'script':str(SCRIPT),'script_sha256':p.digest(SCRIPT),'fixture_root':str(root),
    'passed':len(results),'results':results}
out=root/'results.json';out.write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n')
print(json.dumps({'passed':len(results),'report':str(out),'fixture_root':str(root),'script_sha256':report['script_sha256']},ensure_ascii=False),flush=True)
