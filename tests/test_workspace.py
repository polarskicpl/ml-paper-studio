import copy
import importlib.util
import json
import pathlib
import shutil
import subprocess
import sys
import tempfile

sys.dont_write_bytecode=True
SCRIPT=pathlib.Path(__file__).resolve().parents[1]/"skills/ml-paper-studio/scripts/paper_workspace.py"
compile(SCRIPT.read_text(),str(SCRIPT),'exec')
spec=importlib.util.spec_from_file_location('workspace',SCRIPT)
p=importlib.util.module_from_spec(spec);spec.loader.exec_module(p)
root=pathlib.Path(tempfile.mkdtemp(prefix="ml-paper-studio-regression-"))
base=root/'base';base.mkdir()
results=[]

def put(w,role,value):
    path=w/p.PATHS[role];path.parent.mkdir(parents=True,exist_ok=True)
    path.write_text(json.dumps(value),encoding='utf-8')

def get(w,role):return json.loads((w/p.PATHS[role]).read_text())
def call(w,*args):
    completed=subprocess.run([sys.executable,str(SCRIPT),*args,'--workspace',str(w)],capture_output=True,text=True)
    try:report=json.loads(completed.stdout or completed.stderr)
    except Exception:report={'unparsed_stdout':completed.stdout,'unparsed_stderr':completed.stderr}
    assert 'Traceback' not in completed.stderr,completed.stderr
    return completed.returncode,report

def check(w,stage,expected=0,code=None):
    status,report=call(w,'check','--stage',str(stage))
    assert status==expected,(status,report)
    if code:assert any(f['code']==code for f in report.get('findings',[])),report
    return report

def case(name,action):
    w=root/name;shutil.copytree(base,w,symlinks=True)
    try:action(w);results.append({'case':name,'status':'pass'})
    except Exception as exc:
        results.append({'case':name,'status':'fail','error':str(exc)})
        raise

assert call(base,'init','--project-root',str(root),'--paper-id','fixture')[0]==0
for name in ['evidence/source.py','outline/outline.zh.md','literature/positioning.zh.md',
             'literature/prior-art-matrix.csv','literature/search-ledger.jsonl','manuscript/manuscript.zh.md',
             'manuscript/manuscript.en.md','paper/main.tex','paper/settings.cfg','paper/notes.txt']:
    path=base/name;path.parent.mkdir(parents=True,exist_ok=True);path.write_text('fixture\n')
(base/'paper/main.tex').write_text('\\documentclass{article}\n\\begin{document}\\input{settings.cfg}\\end{document}\n')
(base/'paper/paper.pdf').write_bytes(b'%PDF-static-fixture\n')
put(base,'evidence',{'schema':'ml-paper-studio.evidence/1','records':[{'id':'EV1','root':'workspace','path':'evidence/source.py','sha256':p.digest(base/'evidence/source.py'),'locator':'line 1','kind':'code','status':'observed','conditions':{},'interpretation':'fixture'}],
 'claims':[{'id':'C1','text':'Fixture claim','claim_type':'implementation','evidence_ids':['EV1'],'source_ids':['S1'],'status':'supported','use_in_manuscript':True,'scope':'fixture'}]})
put(base,'sources',{'schema':'ml-paper-studio.sources/1','entries':[{'id':'S1','title':'Fixture','authors':['A'],'year':2026,'identifiers':{'url':'https://example.com'},'canonical_url':'https://example.com','identity_status':'verified','retrieval_status':'full_text','checked_at':'fixture'}]})
(base/p.PATHS['source_support']).write_text('claim_id,source_id,locator,relation,support_status\nC1,S1,p1,supports,supported\n')
put(base,'review',{'schema':'ml-paper-studio.review/1','rounds':[{'round':1,'type':'evidence_self_review','reviewer_mode':'same_model','findings':[],'changes':[]},{'round':2,'type':'simulated_review','reviewer_mode':'same_model','findings':[],'changes':[]}],'unresolved':[]})
put(base,'translation',{'schema':'ml-paper-studio.translation/1','source_sha256':p.digest(base/p.PATHS['chinese']),'target_sha256':p.digest(base/p.PATHS['english']),'checks':{k:{'status':'pass','evidence':'static fixture'} for k in ['numbers','formulas','citation_attachment','claim_strength','terminology']},'entries':[]})
put(base,'venue',{'schema':'ml-paper-studio.venue/1','target':{k:'fixture' for k in ['venue','year','track','paper_type','phase']},'status':'verified','conflicts':[],'rules':[{'id':'R1','requirement':'fixture','source_url':'https://example.com','locator':'fixture','checked_at':'fixture','status':'verified'}],'template':{'status':'verified','manifest_path':'venue/template-manifest.json'}})
(base/'venue/template-manifest.json').write_text('{}')
put(base,'build',{'schema':'ml-paper-studio.build/1','status':'success','engine':'fixture','command_or_tool':'fixture','built_at':'fixture','source_manifest':p.paper_inputs(base),'pdf_path':'paper/paper.pdf','pdf_sha256':p.digest(base/'paper/paper.pdf'),'diagnostics':[]})
put(base,'pdf_check',{'schema':'ml-paper-studio.pdf-check/1','pdf_sha256':p.digest(base/'paper/paper.pdf'),'checks':{k:{'status':'pass','evidence':'static fixture'} for k in ['content_fidelity','references','math','layout_visual','page_limit','anonymity','fonts']}})
assert call(base,'confirm-outline','--user-message-ref','fixture','--quote','synthetic fixture only','--scope','fixture')[0]==0
for stage in range(6):check(base,stage)
results.append({'case':'baseline_all_six_stages','status':'pass','scope':'synthetic static interfaces only; no real compilation or approval claimed'})

def mutate(w,role,action):
    data=get(w,role);action(data);put(w,role,data)

def bad_json(w,role,stage,value):
    put(w,role,value)
    original=(w/p.PATHS[role]).read_bytes()
    status,report=call(w,'check','--stage',str(stage))
    assert status==2 and report['status']=='invalid_input',report
    assert (w/p.PATHS[role]).read_bytes()==original

def bad_state(w,value,command='status'):
    path=w/'paper-state.json';path.write_text(json.dumps(value));before=path.read_bytes()
    status,report=call(w,command)
    assert status==2 and report['status']=='invalid_input',report
    assert path.read_bytes()==before

case('state_root_list',lambda w:bad_state(w,[]))
for key,value in [('artifact_paths',[]),('framework_confirmation',[]),('settings',None),('stages',[]),('history',{})]:
    def action(w,key=key,value=value):
        state=json.loads((w/'paper-state.json').read_text());state[key]=value;bad_state(w,state)
    case('state_shape_'+key,action)
for role,stage,value in [
 ('venue',0,{'schema':'ml-paper-studio.venue/1','target':[]}),
 ('evidence',1,{'schema':'ml-paper-studio.evidence/1','records':[None],'claims':[]}),
 ('sources',2,{'schema':'ml-paper-studio.sources/1','entries':[{'identifiers':[]}]}),
 ('review',3,{'schema':'ml-paper-studio.review/1','rounds':[None]}),
 ('translation',4,{'schema':'ml-paper-studio.translation/1','checks':[]}),
 ('build',5,{'schema':'ml-paper-studio.build/1','source_manifest':[None]}),
 ('pdf_check',5,{'schema':'ml-paper-studio.pdf-check/1','checks':{'layout_visual':None}}),
 ]:
    case('json_shape_'+role,lambda w,role=role,stage=stage,value=value:bad_json(w,role,stage,value))

def repeat_init(w):
    before=(w/'paper-state.json').read_bytes()
    assert call(w,'init','--project-root',str(root),'--paper-id','overwrite')[0]==2
    assert (w/'paper-state.json').read_bytes()==before
case('init_no_overwrite',repeat_init)
case('cfg_change_stales_pdf',lambda w:((w/'paper/settings.cfg').write_text('changed'),check(w,5,1,'stale_pdf_inputs')))
case('txt_change_stales_pdf',lambda w:((w/'paper/notes.txt').write_text('changed'),check(w,5,1,'stale_pdf_inputs')))
case('unknown_suffix_new_input_stales_pdf',lambda w:((w/'paper/new.custom').write_text('new'),check(w,5,1,'stale_pdf_inputs')))
case('deleted_input_stales_pdf',lambda w:((w/'paper/settings.cfg').unlink(),check(w,5,1,'stale_pdf_inputs')))
def intermediates(w):
    for suffix in ['aux','log','fls','fdb_latexmk','synctex.gz','blg','bcf','run.xml','toc','out']:(w/('paper/main.'+suffix)).write_text('generated')
    (w/'paper/.git').mkdir();(w/'paper/.git/config').write_text('ignored')
    check(w,5)
case('known_intermediates_and_git_ignored',intermediates)
def bad_symlink(w,kind):
    outside=root/'outside';outside.mkdir(exist_ok=True);(outside/'chapter.tex').write_text('fixture')
    if kind=='outside_dir':(w/'paper/sections').symlink_to(outside,target_is_directory=True)
    elif kind=='inside_dir':(w/'paper/sections').symlink_to(w/'evidence',target_is_directory=True)
    else:(w/'paper/escape.tex').symlink_to(outside/'chapter.tex')
    status,report=call(w,'snapshot-inputs');assert status==2 and report['status']=='invalid_input',report
for kind in ['outside_dir','inside_dir','outside_file']:case('symlink_'+kind,lambda w,kind=kind:bad_symlink(w,kind))
def inside_file(w):
    (w/'paper/alias.cfg').symlink_to(w/'paper/settings.cfg')
    manifest=p.paper_inputs(w);assert any(row['path']=='paper/alias.cfg' for row in manifest)
case('inside_file_symlink_tracked',inside_file)

def matrix(w,text,code='invalid_support_status',stage=2):
    (w/p.PATHS['source_support']).write_text('claim_id,source_id,locator,relation,support_status\n'+text+'\n')
    check(w,stage,1,code)
case('matrix_unknown_claim',lambda w:matrix(w,'C404,S1,p1,supports,supported','unknown_support_claim'))
case('matrix_unknown_source',lambda w:matrix(w,'C1,S404,p1,supports,supported','unknown_support_source'))
case('matrix_enum_typo',lambda w:matrix(w,'C1,S1,p1,TYPO,TYPO'))
case('matrix_incompatible_status',lambda w:matrix(w,'C1,S1,p1,context,supported'))
case('matrix_context_cannot_support_core',lambda w:matrix(w,'C1,S1,p1,context,context_only','unsupported_claim_source',1))
case('matrix_unverified_cannot_support_core',lambda w:matrix(w,'C1,S1,p1,supports,unverified','unsupported_claim_source',1))
case('matrix_empty_locator_cannot_support_core',lambda w:matrix(w,'C1,S1,,supports,supported','unsupported_citation',1))
def dangling(w):
    mutate(w,'evidence',lambda d:d['claims'][0].update(source_ids=['S404']))
    check(w,1,1,'missing_source_id');check(w,2,1,'missing_source_id')
case('dangling_source_ids_rejected_in_stages_1_2',dangling)
def unqualified(w,field,value):
    mutate(w,'sources',lambda d:d['entries'][0].update({field:value}))
    check(w,1,1,'unsupported_citation');check(w,2,1,'unsupported_citation')
case('metadata_only_not_support',lambda w:unqualified(w,'retrieval_status','metadata_only'))
case('unverified_identity_not_support',lambda w:unqualified(w,'identity_status','unverified'))
def unresolved(w):
    mutate(w,'evidence',lambda d:d['claims'][0].update(status='unresolved',source_ids=['S404'],evidence_ids=[]))
    check(w,1)
case('unresolved_stage1_candidate_allowed',unresolved)
def partial(w):
    (w/p.PATHS['source_support']).write_text('claim_id,source_id,locator,relation,support_status\nC1,S1,p1,partial,partial\n')
    check(w,1);check(w,2)
case('partial_support_binding_allowed',partial)

case('review_missing_metadata',lambda w:(put(w,'review',{'schema':'ml-paper-studio.review/1','rounds':[{'findings':[]},{'findings':[]}],'unresolved':[]}),check(w,3,1,'invalid_review_round')))
case('review_duplicate_round_ids',lambda w:(mutate(w,'review',lambda d:d['rounds'][1].update(round=1)),check(w,3,1,'duplicate_review_round')))
case('review_duplicate_purposes',lambda w:(mutate(w,'review',lambda d:d['rounds'][1].update(type='evidence_self_review')),check(w,3,1,'review_purposes_missing')))
case('review_unknown_type',lambda w:(mutate(w,'review',lambda d:d['rounds'][1].update(type='TYPO')),check(w,3,1,'unknown_review_type')))
case('review_unknown_reviewer_mode',lambda w:(mutate(w,'review',lambda d:d['rounds'][1].update(reviewer_mode='TYPO')),check(w,3,1,'unknown_reviewer_mode')))
case('review_unresolved_major',lambda w:(mutate(w,'review',lambda d:d['rounds'][1].update(findings=[{'id':'F1','severity':'major','location':'fixture','issue':'fixture','evidence':'fixture','status':'unresolved','resolution':''}])),check(w,3,1,'unresolved_review_issue')))
case('review_unknown_finding_severity',lambda w:(mutate(w,'review',lambda d:d['rounds'][1].update(findings=[{'id':'F1','severity':'TYPO','location':'fixture','issue':'fixture','evidence':'fixture','status':'fixed','resolution':'fixture'}])),check(w,3,1,'unknown_review_finding_status')))
for key in ['content_fidelity','references','math','layout_visual','page_limit','fonts']:
    case('pdf_'+key+'_na_rejected',lambda w,key=key:(mutate(w,'pdf_check',lambda d:d['checks'][key].update(status='not_applicable',reason='not reviewed')),check(w,5,1,'pdf_check_not_completed')))
case('pdf_anonymity_reason_na_allowed',lambda w:(mutate(w,'pdf_check',lambda d:d['checks']['anonymity'].update(status='not_applicable',reason='identified camera-ready fixture')),check(w,5)))
case('pdf_anonymity_empty_na_rejected',lambda w:(mutate(w,'pdf_check',lambda d:d['checks']['anonymity'].update(status='not_applicable',reason=' ')),check(w,5,1,'pdf_check_not_completed')))
case('manifest_duplicate_path_rejected',lambda w:(mutate(w,'build',lambda d:d['source_manifest'].append(copy.deepcopy(d['source_manifest'][0]))),check(w,5,1,'build_binding')))
case('confirmation_changed_outline',lambda w:((w/p.PATHS['outline']).write_text('changed'),check(w,3,1,'confirmation_version_changed')))
case('translation_changed_english',lambda w:((w/p.PATHS['english']).write_text('changed'),check(w,4,1,'stale_translation_check')))

def unverified_nullable(w,missing_url=False,missing_year=False):
    mutate(w,'evidence',lambda d:d['claims'][0].update(status='unresolved'))
    def source_update(d):
        row=d['entries'][0]
        row.update(identity_status='unverified',retrieval_status='metadata_only',canonical_url=None,year=None)
        if missing_url:row.pop('canonical_url')
        if missing_year:row.pop('year')
    mutate(w,'sources',source_update)
    (w/p.PATHS['source_support']).write_text('claim_id,source_id,locator,relation,support_status\nC1,S1,,unclear,unverified\n')
    check(w,2)
case('unverified_canonical_url_and_year_null_allowed',unverified_nullable)
case('unverified_canonical_url_missing_allowed',lambda w:unverified_nullable(w,missing_url=True))
case('unverified_year_missing_allowed',lambda w:unverified_nullable(w,missing_year=True))
def verified_missing_identity(w,field):
    mutate(w,'sources',lambda d:d['entries'][0].update({field:None}))
    check(w,1,1,'doi_only_verification');check(w,2,1,'doi_only_verification')
case('verified_null_canonical_url_not_support',lambda w:verified_missing_identity(w,'canonical_url'))
case('verified_null_year_not_support',lambda w:verified_missing_identity(w,'year'))
def invalid_source_scalar(w,field,value):
    data=get(w,'sources');data['entries'][0][field]=value
    bad_json(w,'sources',2,data)
case('canonical_url_nonstring_rejected',lambda w:invalid_source_scalar(w,'canonical_url',2026))
case('year_string_rejected',lambda w:invalid_source_scalar(w,'year','2026'))
case('year_bool_rejected',lambda w:invalid_source_scalar(w,'year',True))
case('year_float_rejected',lambda w:invalid_source_scalar(w,'year',2026.0))

report={'scope':'local synthetic fixtures only; standard library; no network; no research data; no real paper execution','script':str(SCRIPT),'sha256':p.digest(SCRIPT),'fixture_root':str(root),'passed':len(results),'results':results}
out=root/"results.json";out.write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n')
print(json.dumps({'passed':len(results),'report':str(out),'fixture_root':str(root),'script_sha256':report['sha256']},ensure_ascii=False),flush=True)
