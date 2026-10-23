#!/usr/bin/env python3
"""Local workflow interfaces and byte bindings; never a scientific-validity verifier."""
from __future__ import annotations
import argparse
import csv
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import re
import sys
import time

STAGES = ['00-venue', '01-evidence-outline', '02-literature', '03-draft-review-zh', '04-english', '05-latex-pdf']
PATHS = {
    'venue': 'venue/requirements.json', 'evidence': 'evidence/evidence-map.json',
    'outline': 'outline/outline.zh.md', 'sources': 'literature/sources.json',
    'positioning': 'literature/positioning.zh.md', 'source_support': 'literature/evidence-matrix.csv',
    'prior_art': 'literature/prior-art-matrix.csv', 'search_ledger': 'literature/search-ledger.jsonl',
    'chinese': 'manuscript/manuscript.zh.md', 'english': 'manuscript/manuscript.en.md',
    'review': 'review/review-log.json', 'translation': 'checks/translation-map.json',
    'build': 'checks/build.json', 'pdf_check': 'checks/pdf-check.json', 'pdf': 'paper/paper.pdf',
}
BUILD_INTERMEDIATE_SUFFIXES = {'.aux','.log','.fls','.fdb_latexmk','.synctex','.synctex.gz',
    '.blg','.bcf','.run.xml','.toc','.out','.lof','.lot','.nav','.snm','.vrb','.xdv','.dvi'}
STAGE_STATUSES = {'not_started','in_progress','waiting_author','blocked','drafted','complete','stale'}
SUPPORT_COMBINATIONS = {'supports': {'supported','partial','unverified'},
    'partial': {'partial','unverified'}, 'contradicts': {'contradicted','unverified'},
    'context': {'context_only','unverified'}, 'unclear': {'unverified'}}

def object_value(value, label):
    if not isinstance(value,dict):
        raise ValueError(label + ' must be a JSON object')
    return value

def list_value(value, label, objects=False, strings=False):
    if not isinstance(value,list):
        raise ValueError(label + ' must be a JSON array')
    if objects and any(not isinstance(item,dict) for item in value):
        raise ValueError(label + ' must contain JSON objects')
    if strings and any(not isinstance(item,str) for item in value):
        raise ValueError(label + ' must contain strings')
    return value

def fields(value, label, object_fields=(), list_fields=(), object_lists=(), string_lists=(), string_fields=()):
    object_value(value,label)
    for key in object_fields:
        if key in value:
            object_value(value[key],label+'.'+key)
    for key in list_fields:
        if key in value:
            list_value(value[key],label+'.'+key)
    for key in object_lists:
        if key in value:
            list_value(value[key],label+'.'+key,objects=True)
    for key in string_lists:
        if key in value:
            list_value(value[key],label+'.'+key,strings=True)
    for key in string_fields:
        if key in value and not isinstance(value[key],str):
            raise ValueError(label+'.'+key+' must be a string')

def validate_state(state):
    fields(state,'paper-state',object_fields=('stages','artifact_paths','framework_confirmation','settings'),
        list_fields=('open_decisions','unresolved_evidence'),object_lists=('history',),
        string_fields=('schema','paper_id','project_root','requested_scope'))
    if state.get('schema') != 'ml-paper-studio.state/1':
        raise ValueError('Unsupported state schema')
    if 'requested_scope' in state and state['requested_scope'] not in ['full','stage','section']:
        raise ValueError('requested_scope must be full, stage or section')
    for role,path in state.get('artifact_paths',{}).items():
        if not isinstance(path,str):
            raise ValueError('artifact_paths.'+str(role)+' must be a relative path string')
    for name,item in state.get('stages',{}).items():
        fields(item,'stages.'+name,list_fields=('artifacts',),string_fields=('status',))
        if item.get('status') not in STAGE_STATUSES:
            raise ValueError('Unknown stage status: '+str(item.get('status')))
    if 'current_stage' in state and (type(state['current_stage']) is not int or state['current_stage'] not in range(6)):
        raise ValueError('current_stage must be an integer from 0 to 5')
    confirmation=state.get('framework_confirmation',{})
    fields(confirmation,'framework_confirmation',object_fields=('artifact_sha256',),
        string_fields=('status','user_message_ref','quote','confirmed_scope','confirmed_at'))
    for role,value in confirmation.get('artifact_sha256',{}).items():
        if not isinstance(value,str):
            raise ValueError('framework_confirmation.artifact_sha256.'+str(role)+' must be a string')
    for key in ['review_rounds','max_review_rounds']:
        setting=state.get('settings',{}).get(key,2 if key=='review_rounds' else 3)
        if type(setting) is not int or setting<1:
            raise ValueError('settings.'+key+' must be a positive integer')

def validate_artifact(value, role):
    """Reject wrong JSON shapes before callers dereference nested fields."""
    object_value(value,role)
    if role=='venue':
        fields(value,role,object_fields=('target','template'),object_lists=('rules',),list_fields=('conflicts',))
        fields(value.get('template',{}),'venue.template',string_fields=('status',))
        manifest=value.get('template',{}).get('manifest_path')
        if manifest is not None and not isinstance(manifest,str):
            raise ValueError('venue.template.manifest_path must be a string or null')
        for row in value.get('rules',[]):
            fields(row,'venue.rules',string_fields=('id','requirement','source_url','locator','checked_at','status'))
    elif role=='evidence':
        fields(value,role,object_lists=('records','claims'))
        for row in value.get('records',[]):
            fields(row,'evidence.records',object_fields=('conditions',),
                string_fields=('id','root','path','sha256','locator','kind','status','interpretation'))
        for row in value.get('claims',[]):
            fields(row,'evidence.claims',string_lists=('evidence_ids','source_ids'),
                string_fields=('id','text','claim_type','status','scope'))
            if 'use_in_manuscript' in row and type(row['use_in_manuscript']) is not bool:
                raise ValueError('evidence.claims.use_in_manuscript must be a boolean')
    elif role=='sources':
        fields(value,role,object_lists=('entries',))
        for row in value.get('entries',[]):
            fields(row,'sources.entries',object_fields=('identifiers',),string_lists=('authors',),
                string_fields=('id','title','identity_status','retrieval_status'))
            if row.get('canonical_url') is not None and not isinstance(row['canonical_url'],str):
                raise ValueError('sources.entries.canonical_url must be a string or null')
            if row.get('year') is not None and type(row['year']) is not int:
                raise ValueError('sources.entries.year must be an integer or null')
            if any(item is not None and not isinstance(item,str) for item in row.get('identifiers',{}).values()):
                raise ValueError('sources.entries.identifiers values must be strings or null')
    elif role=='review':
        fields(value,role,object_lists=('rounds',),list_fields=('unresolved',))
        for round_ in value.get('rounds',[]):
            fields(round_,'review.rounds',object_lists=('findings',),list_fields=('changes',),
                string_fields=('type','reviewer_mode'))
            for finding in round_.get('findings',[]):
                fields(finding,'review.findings',string_fields=('id','severity','status'))
    elif role in ['translation','pdf_check']:
        fields(value,role,object_fields=('checks',),list_fields=('entries',))
        for key,item in value.get('checks',{}).items():
            fields(item,role+'.checks.'+key,string_fields=('status',))
    elif role=='build':
        fields(value,role,object_lists=('source_manifest',),list_fields=('diagnostics',),
            string_fields=('status','pdf_path'))
        for row in value.get('source_manifest',[]):
            fields(row,'build.source_manifest',string_fields=('path','sha256'))
            if not row.get('path') or not row.get('sha256'):
                raise ValueError('build.source_manifest entries require path and sha256')

def now():
    return datetime.now(timezone.utc).isoformat()

def inside(root, relative):
    root = Path(root).resolve()
    if not isinstance(relative,str):
        raise ValueError('Expected a relative path string')
    rel = Path(relative)
    if rel.is_absolute():
        raise ValueError('Expected a relative path: ' + str(relative))
    result = (root / rel).resolve()
    if not result.is_relative_to(root):
        raise ValueError('Path escapes the declared root: ' + str(relative))
    return result

def digest(path, allow_large=False):
    path = Path(path)
    if path.stat().st_size > 64 * 1024 * 1024 and not allow_large:
        raise ValueError('Large source requires --hash-large or an existing small provenance manifest: ' + str(path))
    hasher = hashlib.sha256()
    start = last = time.monotonic()
    total = 0
    with path.open('rb') as stream:
        while chunk := stream.read(1024 * 1024):
            hasher.update(chunk)
            total += len(chunk)
            if time.monotonic() - last >= 15:
                print('[文件核对] {} bytes={} elapsed={:.1f}s'.format(path.name,total,time.monotonic()-start),file=sys.stderr,flush=True)
                last = time.monotonic()
    return hasher.hexdigest()

def save(path, value, exclusive=False):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    data = json.dumps(value,ensure_ascii=False,indent=2) + '\n'
    if exclusive:
        with path.open('x',encoding='utf-8') as output:
            output.write(data)
    else:
        temporary = path.with_name(path.name + '.updating')
        with temporary.open('x',encoding='utf-8') as output:
            output.write(data)
        temporary.replace(path)

def state_at(workspace):
    workspace = Path(workspace).resolve(strict=True)
    if not workspace.is_dir():
        raise ValueError('Workspace must be an existing directory')
    state = json.loads(inside(workspace,'paper-state.json').read_text(encoding='utf-8'))
    validate_state(state)
    return workspace, state

def paper_inputs(workspace, pdf_relative='paper/paper.pdf', hash_large=False):
    workspace = Path(workspace).resolve(strict=True)
    if (workspace/'paper').is_symlink():
        raise ValueError('Symlink directories are not supported in build inputs: paper/')
    root = inside(workspace,'paper')
    if not root.is_dir():
        raise ValueError('paper/ does not exist')
    pdf = inside(workspace,pdf_relative)
    result = []
    def visit(directory):
        for path in sorted(directory.iterdir()):
            if path.name=='.git':
                continue
            rel = path.relative_to(workspace).as_posix()
            if path.is_symlink() and path.is_dir():
                raise ValueError('Symlink directories are not supported in build inputs: '+rel)
            safe = inside(workspace,rel)
            if path.is_dir():
                visit(path)
            elif path.is_file():
                if safe!=pdf and not path.name.lower().endswith(tuple(BUILD_INTERMEDIATE_SUFFIXES)):
                    result.append({'path':rel,'sha256':digest(safe,hash_large)})
            elif path.is_symlink():
                raise ValueError('Build input symlink does not resolve to a regular file: '+rel)
    visit(root)
    return result

class Checker:
    def __init__(self, workspace, state, hash_large=False):
        validate_state(state)
        self.workspace,self.state,self.hash_large = workspace,state,hash_large
        self.findings = []
        self.inspected = {}

    def add(self, severity, code, message, path=None):
        item = {'severity':severity,'code':code,'message':message}
        if path is not None:
            item['path'] = str(path)
        self.findings.append(item)

    def path(self, role):
        return inside(self.workspace,self.state.get('artifact_paths',{}).get(role,PATHS[role]))

    def file(self, role, optional=False):
        path = self.path(role)
        if not path.is_file():
            if not optional:
                self.add('error','missing_artifact','Required artifact is missing',path)
            return None
        self.inspected[role] = str(path)
        return path

    def obj(self, role, schema=None, optional=False):
        path = self.file(role,optional)
        if path is None:
            return {}
        value = json.loads(path.read_text(encoding='utf-8'))
        object_value(value,role)
        if schema and value.get('schema') != schema:
            raise ValueError('Expected schema ' + str(schema)+' in '+str(path))
        validate_artifact(value,role)
        return value

    def venue(self):
        obj = self.obj('venue','ml-paper-studio.venue/1')
        target = obj.get('target',{})
        missing = [key for key in ['venue','year','track','paper_type','phase'] if not target.get(key)]
        if missing:
            self.add('error','target_unconfirmed','Official compliance is unresolved: ' + ', '.join(missing))
        if obj.get('status') != 'verified':
            self.add('error','venue_unverified','Venue rules are not verified for this exact target')
        if obj.get('conflicts'):
            self.add('error','venue_conflicts','Unresolved official-rule conflicts remain')
        rules = obj.get('rules',[])
        if not rules:
            self.add('error','missing_rules','No applicable sourced rules are recorded')
        for rule in rules:
            if not all(rule.get(k) for k in ['id','requirement','source_url','locator','checked_at']) or rule.get('status') != 'verified':
                self.add('error','unsourced_rule','Rule lacks a source, applicability check or resolution: ' + str(rule.get('id')))
        template = obj.get('template',{})
        if template.get('status') != 'verified' or not template.get('manifest_path'):
            self.add('error','template_unverified','A verified official-template binding is required for final venue compliance')
        elif not inside(self.workspace,template['manifest_path']).is_file():
            self.add('error','missing_template_manifest','The active template manifest is missing')

    def evidence(self):
        obj = self.obj('evidence','ml-paper-studio.evidence/1')
        records,claims = obj.get('records',[]),obj.get('claims',[])
        if not records or not claims:
            self.add('error','empty_evidence','Evidence records and scoped claims are both required')
        ids = [r.get('id') for r in records]
        if any(not i for i in ids) or len(ids)!=len(set(ids)):
            self.add('error','duplicate_evidence_id','Missing or duplicate evidence identifiers')
        lookup = {r.get('id'):r for r in records}
        for record in records:
            status = record.get('status')
            if status not in ['observed','author_reported','planned','synthetic','partial','failed']:
                self.add('error','unknown_evidence_status','Evidence status is not classified: '+str(record.get('id')))
            if record.get('kind') not in ['code','result','protocol','log','theory','data','figure']:
                self.add('error','unknown_evidence_kind','Evidence kind is not classified: '+str(record.get('id')))
            if status not in ['observed','partial']:
                continue
            try:
                anchor = record.get('root','project')
                if anchor not in ['project','workspace']:
                    raise ValueError('Unknown evidence root')
                root = self.workspace if anchor=='workspace' else Path(self.state['project_root']).resolve(strict=True)
                path = inside(root,record['path'])
                if not record.get('locator') or not record.get('sha256'):
                    raise ValueError('Observed evidence requires locator and SHA256')
                actual = digest(path,self.hash_large)
                if actual != record['sha256']:
                    self.add('error','changed_evidence','Evidence bytes changed: '+str(record.get('id')),path)
            except (KeyError, OSError, ValueError) as exc:
                level = 'warning' if 'Large source requires' in str(exc) else 'error'
                self.add(level,'evidence_binding',str(exc))
        cids = [c.get('id') for c in claims]
        if any(not i for i in cids) or len(cids)!=len(set(cids)):
            self.add('error','duplicate_claim_id','Missing or duplicate claim identifiers')
        for claim in claims:
            if claim.get('status') not in ['supported','bounded','unresolved','contradicted']:
                self.add('error','unknown_claim_status','Claim status is not classified: '+str(claim.get('id')))
            if claim.get('claim_type') not in ['empirical','implementation','theory','positioning']:
                self.add('error','unknown_claim_type','Claim type is not classified: '+str(claim.get('id')))
            if claim.get('use_in_manuscript',True) is False:
                continue
            refs = claim.get('evidence_ids',[])
            if any(ref not in lookup for ref in refs):
                self.add('error','missing_evidence_id','Claim points to missing evidence: '+str(claim.get('id')))
            if claim.get('status') in ['supported','bounded']:
                if not refs and not claim.get('source_ids'):
                    self.add('error','unsupported_claim','Claim is labeled supported without evidence: '+str(claim.get('id')))
                if claim.get('claim_type') == 'empirical' and not any(lookup.get(r,{}).get('kind')=='result' and lookup.get(r,{}).get('status') in ['observed','partial'] for r in refs):
                    self.add('error','nonobserved_result','Empirical claim lacks an observed scoped result: '+str(claim.get('id')))
        if any(c.get('use_in_manuscript',True) and c.get('status') in ['supported','bounded'] and c.get('source_ids') for c in claims):
            self.source_bindings(obj)
        return obj

    def source_bindings(self, evidence=None):
        """Validate identifiers and recorded support, without judging source meaning."""
        evidence = self.obj('evidence','ml-paper-studio.evidence/1') if evidence is None else evidence
        claims=evidence.get('claims',[])
        claim_ids=[claim.get('id') for claim in claims]
        if any(not key for key in claim_ids) or len(claim_ids)!=len(set(claim_ids)):
            self.add('error','duplicate_claim_id','Missing or duplicate claim identifiers')
        claim_lookup={claim.get('id'):claim for claim in claims}
        for claim in claims:
            if claim.get('status') not in ['supported','bounded','unresolved','contradicted'] or claim.get('claim_type') not in ['empirical','implementation','theory','positioning']:
                self.add('error','invalid_support_claim','Support matrix claim has an unknown status/type: '+str(claim.get('id')))
        obj = self.obj('sources','ml-paper-studio.sources/1')
        entries = obj.get('entries',[])
        sources = {r.get('id'):r for r in entries}
        if len(sources)!=len(entries) or any(not k for k in sources):
            self.add('error','duplicate_source_id','Missing or duplicate source identifiers')
        for source in entries:
            if source.get('identity_status') not in ['verified','mismatch','uncertain','unverified']:
                self.add('error','unknown_identity_status','Unclassified identity status: '+str(source.get('id')))
            if source.get('identity_status') == 'verified':
                if not all(source.get(k) for k in ['title','authors','year','canonical_url','checked_at']) or not isinstance(source.get('authors'),list) or not any(source.get('identifiers',{}).values()):
                    self.add('error','doi_only_verification','Verified reference lacks required identity fields: '+str(source.get('id')))
            if source.get('retrieval_status') not in ['full_text','abstract_only','metadata_only','unavailable']:
                self.add('error','unknown_retrieval_status','Unclassified retrieval status: '+str(source.get('id')))
        path = self.file('source_support')
        valid_pairs=set()
        if path:
            try:
                with path.open(encoding='utf-8',newline='') as handle:
                    reader = csv.DictReader(handle)
                    required={'claim_id','source_id','locator','relation','support_status'}
                    if not required.issubset(reader.fieldnames or []) or len(reader.fieldnames)!=len(set(reader.fieldnames)):
                        raise ValueError('Source-support matrix is missing required columns')
                    for row in reader:
                        if None in row or any(row[key] is None for key in required):
                            raise ValueError('Source-support matrix has a row with the wrong number of fields')
                        row={key:value.strip() if isinstance(value,str) else value for key,value in row.items()}
                        claim_id,source_id=row['claim_id'],row['source_id']
                        src = sources.get(source_id)
                        known_claim=claim_id in claim_lookup
                        if not known_claim:
                            self.add('error','unknown_support_claim','Unknown claim '+claim_id)
                        relation,status=row['relation'],row['support_status']
                        compatible=relation in SUPPORT_COMBINATIONS and status in SUPPORT_COMBINATIONS[relation]
                        if not compatible:
                            self.add('error','invalid_support_status','Unknown or incompatible relation/support_status: '+relation+'/'+status)
                        if not src:
                            self.add('error','unknown_support_source','Unknown source '+source_id)
                        elif status in ['supported','partial']:
                            if src.get('identity_status') != 'verified' or src.get('retrieval_status') not in ['full_text','abstract_only'] or not row['locator']:
                                self.add('error','unsupported_citation','Claim support exceeds source identity/access/locator: '+source_id)
                            elif compatible and known_claim:
                                valid_pairs.add((claim_id,source_id))
                                if src.get('retrieval_status')=='abstract_only':
                                    self.add('warning','abstract_scope','Verify that this claim is limited to explicit abstract content: '+claim_id)
            except (OSError, ValueError, csv.Error) as exc:
                self.add('error','invalid_support_matrix',str(exc),path)
        for claim in claims:
            if not claim.get('use_in_manuscript',True) or claim.get('status') not in ['supported','bounded']:
                continue
            for source_id in claim.get('source_ids',[]):
                if source_id not in sources:
                    self.add('error','missing_source_id','Claim points to missing source: '+str(claim.get('id'))+'/'+source_id)
                elif (claim.get('id'),source_id) not in valid_pairs:
                    self.add('error','unsupported_claim_source','Claim/source lacks a verified, readable supported/partial matrix binding: '+str(claim.get('id'))+'/'+source_id)
        return obj

    def literature(self):
        obj=self.source_bindings()
        self.file('positioning')
        self.file('prior_art')
        self.file('search_ledger')
        return obj

    def confirmation(self):
        confirmation = self.state.get('framework_confirmation',{})
        if confirmation.get('status') not in ['human_confirmed','delegated_to_agent'] or not all(confirmation.get(key,'').strip() for key in ['user_message_ref','quote','confirmed_scope']):
            self.add('error','author_confirmation_required','A real author decision on this framework must be recorded')
            return
        for role in ['outline','positioning','evidence']:
            path = self.file(role)
            if path and digest(path,self.hash_large) != confirmation.get('artifact_sha256',{}).get(role):
                self.add('error','confirmation_version_changed','Recheck whether the '+role+' change is substantive; do not silently reuse the old binding',path)

    def chinese(self):
        obj = self.evidence()
        self.file('chinese')
        self.confirmation()
        for claim in obj.get('claims',[]):
            if claim.get('use_in_manuscript',True) and claim.get('status') not in ['supported','bounded']:
                self.add('error','open_core_claim','Unresolved claim remains in scope: '+str(claim.get('id')))
        log = self.obj('review','ml-paper-studio.review/1')
        rounds = log.get('rounds',[])
        required = self.state.get('settings',{}).get('review_rounds',2)
        if len(rounds)<required:
            self.add('error','review_not_completed','Required purposeful review rounds are not recorded')
        if len(rounds)>self.state.get('settings',{}).get('max_review_rounds',3):
            self.add('warning','review_budget_exceeded','Review exceeded the default budget; check explicit user scope')
        round_ids=set()
        purposes=set()
        for round_ in rounds:
            missing=set(['round','type','reviewer_mode','findings','changes'])-round_.keys()
            if missing:
                self.add('error','invalid_review_round','Review round is missing fields: '+', '.join(sorted(missing)))
            round_id=round_.get('round')
            if isinstance(round_id,bool) or not isinstance(round_id,(int,str)) or not str(round_id).strip():
                self.add('error','invalid_review_round_id','Review round requires an integer or nonempty string identifier')
            elif str(round_id) in round_ids:
                self.add('error','duplicate_review_round','Duplicate review round: '+str(round_id))
            else:
                round_ids.add(str(round_id))
            kind=round_.get('type')
            if kind not in ['evidence_self_review','simulated_review','targeted_fix']:
                self.add('error','unknown_review_type','Unknown review purpose: '+str(kind))
            elif not missing:
                purposes.add(kind)
            if round_.get('reviewer_mode') not in ['same_model','independent_agent']:
                self.add('error','unknown_reviewer_mode','Unknown reviewer mode: '+str(round_.get('reviewer_mode')))
            for finding in round_.get('findings',[]):
                missing_finding=set(['id','severity','location','issue','evidence','status','resolution'])-finding.keys()
                if missing_finding:
                    self.add('error','invalid_review_finding','Review finding lacks fields: '+', '.join(sorted(missing_finding)))
                if finding.get('severity') not in ['critical','major','minor','style'] or finding.get('status') not in ['fixed','unresolved','deferred']:
                    self.add('error','unknown_review_finding_status','Review finding has an unknown severity/status: '+str(finding.get('id')))
                if finding.get('severity') in ['critical','major'] and finding.get('status')!='fixed':
                    self.add('error','unresolved_review_issue','Core issue is not fixed: '+str(finding.get('id')))
        if required>=2 and not {'evidence_self_review','simulated_review'}.issubset(purposes):
            self.add('error','review_purposes_missing','The two required purposes are evidence_self_review and simulated_review')
        if log.get('unresolved'):
            self.add('warning','review_unresolved_list','Review still lists unresolved matters; classify their actual impact')

    def english(self):
        zh,en = self.file('chinese'),self.file('english')
        obj = self.obj('translation','ml-paper-studio.translation/1')
        for name,path in [('source',zh),('target',en)]:
            if path and obj.get(name+'_sha256')!=digest(path,self.hash_large):
                self.add('error','stale_translation_check',name+' content changed after fidelity review')
        for key in ['numbers','formulas','citation_attachment','claim_strength','terminology']:
            item = obj.get('checks',{}).get(key,{})
            if item.get('status')!='pass' or not item.get('evidence'):
                self.add('error','translation_not_checked','Translation check lacks actual review: '+key)

    def build_binding(self):
        """Check the actual PDF/input binding without asserting venue readiness."""
        obj = self.obj('build','ml-paper-studio.build/1')
        if obj.get('status')!='success' or not all(obj.get(k) for k in ['engine','command_or_tool','built_at']):
            self.add('error','build_not_successful','Actual successful compilation is not recorded')
        pdf = inside(self.workspace,obj.get('pdf_path',PATHS['pdf']))
        if not pdf.is_file():
            self.add('error','pdf_missing','No actual exported PDF exists',pdf)
        else:
            with pdf.open('rb') as handle:
                if handle.read(5)!=b'%PDF-':
                    self.add('error','invalid_pdf_header','File does not start with a PDF header',pdf)
            if obj.get('pdf_sha256')!=digest(pdf,self.hash_large):
                self.add('error','pdf_binding','PDF bytes do not match the build record',pdf)
        manifest = obj.get('source_manifest',[])
        if not manifest:
            self.add('error','missing_build_inputs','No source manifest binds this PDF to its inputs')
        else:
            try:
                current = paper_inputs(self.workspace,obj.get('pdf_path',PATHS['pdf']),self.hash_large)
                expected = {x['path']:x['sha256'] for x in manifest}
                if len(expected)!=len(manifest):
                    raise ValueError('Build source manifest contains duplicate paths')
                actual = {x['path']:x['sha256'] for x in current}
                if actual!=expected:
                    self.add('error','stale_pdf_inputs','Source/template/asset inputs changed, or a current input is missing from the build binding')
            except (OSError,ValueError,KeyError) as exc:
                self.add('error','build_binding',str(exc))
        return obj

    def latex_pdf(self):
        self.venue()
        obj = self.build_binding()
        check = self.obj('pdf_check','ml-paper-studio.pdf-check/1')
        if check.get('pdf_sha256')!=obj.get('pdf_sha256'):
            self.add('error','stale_pdf_check','Visual/submission review is bound to another PDF')
        for key in ['content_fidelity','references','math','layout_visual','page_limit','anonymity','fonts']:
            item = check.get('checks',{}).get(key,{})
            if not (item.get('status')=='pass' and item.get('evidence') or key=='anonymity' and item.get('status')=='not_applicable' and isinstance(item.get('reason'),str) and item['reason'].strip()):
                self.add('error','pdf_check_not_completed','PDF check was not actually completed: '+key)

    def run_draft(self, stage):
        """An explicitly authorized internal handoff; never relax the strict checks."""
        if stage not in [3,4,5]:
            raise ValueError('--purpose draft is supported only for stages 3, 4 and 5')
        drafting=object_value(self.state.get('drafting',{}),'drafting')
        if drafting.get('mode')!='parallel' or not isinstance(drafting.get('declaration_path'),str) or not drafting['declaration_path'].strip():
            raise ValueError('Draft checks require drafting.mode=parallel and declaration_path')
        declaration_path=inside(self.workspace,drafting['declaration_path'])
        declaration=object_value(json.loads(declaration_path.read_text(encoding='utf-8')),'draft declaration')
        if declaration.get('schema')!='ml-paper-studio.draft-declaration/1':
            raise ValueError('Unsupported draft declaration schema')
        authorization=object_value(declaration.get('authorization',{}),'draft authorization')
        if any(not isinstance(authorization.get(key),str) or not authorization[key].strip() for key in ['user_message_ref','quote','scope']):
            raise ValueError('Draft authorization requires an actual message reference, quote and scope')
        pending=list_value(declaration.get('pending'),'draft pending',objects=True)
        self.inspected['draft_declaration']=str(declaration_path)
        evidence=self.evidence()
        claims={row.get('id'):row for row in evidence.get('claims',[])}
        tentative=[row for row in evidence.get('claims',[]) if row.get('use_in_manuscript',True) and row.get('status')=='unresolved' and row.get('source_ids')]
        if tentative:
            sources=self.obj('sources','ml-paper-studio.sources/1')
            source_ids={row.get('id') for row in sources.get('entries',[])}
            for claim in tentative:
                for source_id in claim.get('source_ids',[]):
                    if source_id not in source_ids:
                        self.add('error','missing_source_id','Draft claim points to a missing source: '+str(claim.get('id'))+'/'+source_id)
        texts={}
        for role in ['chinese']+(['english'] if stage==4 else []):
            path=self.file(role)
            if path:
                texts[role]=path.read_text(encoding='utf-8')
        if stage==5:
            path=self.file('english',optional=True)
            if path:
                texts['english']=path.read_text(encoding='utf-8')
        ids=set()
        pending_claims=set()
        active_tokens=set()
        for row in pending:
            if any(not isinstance(row.get(key),str) or not row[key].strip() for key in ['id','claim_id','status','placeholder']):
                raise ValueError('Each draft pending entry requires id, claim_id, status and placeholder strings')
            locations=list_value(row.get('locations'),'draft pending.locations',strings=True)
            if not locations or any(not item.strip() for item in locations) or not isinstance(row.get('required_evidence'),str) or not row['required_evidence'].strip():
                raise ValueError('Each draft pending entry requires nonempty locations and required_evidence')
            if not re.fullmatch(r'[A-Za-z0-9][A-Za-z0-9_-]*',row['id']) or row['placeholder']!='[[RESULT:'+row['id']+']]':
                raise ValueError('Draft placeholders must be [[RESULT:<id>]] with a simple alphanumeric identifier')
            if row['id'] in ids:
                self.add('error','duplicate_draft_id','Duplicate draft ledger identifier: '+row['id'])
            ids.add(row['id'])
            if row['status'] not in ['pending','resolved','dropped']:
                raise ValueError('Draft pending status must be pending, resolved or dropped')
            claim=claims.get(row['claim_id'])
            if not claim:
                self.add('error','unknown_draft_claim','Draft ledger points to a missing claim: '+row['claim_id'])
                continue
            if row['status']=='pending':
                if row['claim_id'] in pending_claims:
                    self.add('error','duplicate_pending_claim','Use one pending entry per claim: '+row['claim_id'])
                pending_claims.add(row['claim_id'])
                active_tokens.add(row['placeholder'])
                if claim.get('status')!='unresolved' or not claim.get('use_in_manuscript',True):
                    self.add('error','pending_claim_status','Pending entries must point to an in-scope unresolved claim: '+row['claim_id'])
                for role,text in texts.items():
                    if row['placeholder'] not in text:
                        self.add('error','missing_draft_placeholder','Pending placeholder is missing from '+role+': '+row['placeholder'])
            elif row['status']=='resolved' and claim.get('status') not in ['supported','bounded']:
                self.add('error','unresolved_ledger_resolution','Resolved entry lacks a supported/bounded claim: '+row['claim_id'])
            elif row['status']=='dropped' and claim.get('use_in_manuscript',True):
                self.add('error','dropped_claim_in_scope','Dropped claim remains in manuscript scope: '+row['claim_id'])
        for claim in evidence.get('claims',[]):
            if not claim.get('use_in_manuscript',True):
                continue
            if claim.get('status')=='contradicted':
                self.add('error','draft_contradicted_claim','A contradicted claim cannot be assumed in a draft: '+str(claim.get('id')))
            elif claim.get('status')=='unresolved' and claim.get('id') not in pending_claims:
                self.add('error','unregistered_draft_claim','In-scope unresolved claim lacks a pending entry: '+str(claim.get('id')))
        for role,text in texts.items():
            for token in set(re.findall(r'\[\[RESULT:[A-Za-z0-9_-]+\]\]',text))-active_tokens:
                self.add('error','orphan_draft_placeholder','Unregistered, resolved or dropped placeholder remains in '+role+': '+token)
        if stage==4:
            self.english()
        elif stage==5:
            self.build_binding()
        errors=sum(item['severity']=='error' for item in self.findings)
        return {'schema':'ml-paper-studio.draft-check/1','stage':STAGES[stage],
            'purpose':'draft','status':'needs_review' if errors else 'draft_consistent',
            'errors':errors,'findings':self.findings,'inspected_artifacts':self.inspected,
            'checked_at':now(),'submission_readiness':'not_assessed',
            'drafting':{'mode':'parallel','scope':'internal_discussion_only',
                'authorization_scope':authorization['scope'],'authorization_authenticated':False,
                'declaration_path':drafting['declaration_path'],'pending':pending},
            'scope':'declared_internal_draft_structure_and_current_byte_bindings_only',
            'not_assessed':['scientific_validity','semantic_claim_support','author_message_authenticity',
                'review_completion','venue_compliance']+(['pdf_visual_and_submission_review'] if stage==5 else []),
            'limitations':['Authorization and ledger locations are caller-reported; this tool does not authenticate or semantically verify them.',
                'Placeholders are checked in manuscript text, not extracted from the rendered PDF. Internal draft prose must not be represented as observed findings.',
                'A clean draft check does not approve a framework, finish a stage, validate scientific results or permit submission.',
                'Build execution is caller-recorded; byte bindings and a PDF header cannot prove actual compilation or rendered PDF quality.',
                'Default hashing skips sources larger than 64 MiB with a warning. Build bindings cover paper/ except known generated files and do not discover external dependencies.']}

    def run(self, stage):
        [self.venue, lambda:(self.evidence(),self.file('outline')),self.literature,self.chinese,self.english,self.latex_pdf][stage]()
        errors = sum(x['severity']=='error' for x in self.findings)
        return {'schema':'ml-paper-studio.workspace-check/1','stage':STAGES[stage],'status':'needs_review' if self.findings else 'consistent','errors':errors,'findings':self.findings,'inspected_artifacts':self.inspected,'checked_at':now(),'scope':'static_structure_and_current_byte_bindings_only','limitations':['Does not prove evidence truth, mathematical correctness, claim support, human authorization, actual compile execution, visual quality or venue compliance.','Approval and pass fields must be grounded in real messages and checks; this tool does not authenticate them.','Default hashing skips sources larger than 64 MiB and reports that limitation.','Build snapshots conservatively track paper/ files except known build intermediates, the selected PDF and .git; they do not discover dependencies outside paper/. Symlink directories are rejected.']}

def main():
    parser = argparse.ArgumentParser(description=__doc__)
    subs = parser.add_subparsers(dest='command',required=True)
    for name in ['init','status','check','confirm-outline','invalidate','snapshot-inputs']:
        command = subs.add_parser(name)
        command.add_argument('--workspace',required=True)
        if name=='init':
            command.add_argument('--project-root',required=True)
            command.add_argument('--paper-id',required=True)
            command.add_argument('--scope',choices=['full','stage','section'],default='full')
        if name=='check':
            command.add_argument('--stage',required=True,type=int,choices=range(6))
            command.add_argument('--hash-large',action='store_true')
            command.add_argument('--purpose',choices=['strict','draft'],default='strict')
        if name=='confirm-outline':
            command.add_argument('--user-message-ref',required=True)
            command.add_argument('--quote',required=True)
            command.add_argument('--scope',required=True)
            command.add_argument('--mode',choices=['human_confirmed','delegated_to_agent'],default='human_confirmed')
        if name=='invalidate':
            command.add_argument('--kind',required=True,choices=['venue','evidence','claims','literature','outline','chinese','english','latex'])
            command.add_argument('--reason',required=True)
        if name=='snapshot-inputs':
            command.add_argument('--pdf',default=PATHS['pdf'])
            command.add_argument('--hash-large',action='store_true')
    args = parser.parse_args()
    if args.command=='init':
        workspace = Path(args.workspace).resolve()
        project = Path(args.project_root).resolve(strict=True)
        if not project.is_dir():
            raise ValueError('Project root is not a directory')
        workspace.mkdir(parents=True,exist_ok=True)
        state = {'schema':'ml-paper-studio.state/1','paper_id':args.paper_id,'project_root':str(project),'requested_scope':args.scope,'current_stage':0,'stages':{s:{'status':'not_started','artifacts':[]} for s in STAGES},'artifact_paths':PATHS,'framework_confirmation':{'status':'not_requested'},'settings':{'review_rounds':2,'max_review_rounds':3},'open_decisions':[],'unresolved_evidence':[],'history':[{'at':now(),'action':'initialized'}]}
        save(inside(workspace,'paper-state.json'),state,exclusive=True)
        print(json.dumps({'status':'initialized','workspace':str(workspace),'created':'paper-state.json'},ensure_ascii=False))
        return 0
    workspace,state = state_at(args.workspace)
    if args.command=='status':
        print(json.dumps(state,ensure_ascii=False,indent=2))
        return 0
    if args.command=='check':
        checker=Checker(workspace,state,args.hash_large)
        report = checker.run_draft(args.stage) if args.purpose=='draft' else checker.run(args.stage)
        print(json.dumps(report,ensure_ascii=False,indent=2))
        return 1 if report['errors'] else 0
    if args.command=='snapshot-inputs':
        print(json.dumps({'schema':'ml-paper-studio.build-inputs/1','captured_at':now(),'source_manifest':paper_inputs(workspace,args.pdf,args.hash_large),'scope':'input_bytes_only_not_a_build_success_record'},ensure_ascii=False,indent=2))
        return 0
    if args.command=='confirm-outline':
        if not args.quote.strip() or not args.user_message_ref.strip() or not args.scope.strip():
            raise ValueError('Confirmation requires an actual message reference, quote and scope')
        bindings = {}
        for role in ['outline','positioning','evidence']:
            bindings[role]=digest(inside(workspace,state.get('artifact_paths',PATHS).get(role,PATHS[role])))
        state['framework_confirmation']={'status':args.mode,'user_message_ref':args.user_message_ref,'quote':args.quote,'confirmed_scope':args.scope,'artifact_sha256':bindings,'confirmed_at':now(),'authority_note':'Caller must have observed the real user message; this record cannot authenticate it.'}
        state['history'].append({'at':now(),'action':'framework_confirmation_recorded','mode':args.mode})
    elif args.command=='invalidate':
        affected={'venue':[0,4,5],'evidence':[1,3,4,5],'claims':[1,2,3,4,5],'literature':[2,3,4,5],'outline':[3,4,5],'chinese':[3,4,5],'english':[4,5],'latex':[5]}[args.kind]
        for stage in affected:
            item=state['stages'][STAGES[stage]]
            if item['status']!='not_started':
                item['status']='stale'
        state['current_stage']=min(affected)
        state['history'].append({'at':now(),'action':'invalidated','kind':args.kind,'stages':affected,'reason':args.reason})
    save(inside(workspace,'paper-state.json'),state)
    print(json.dumps({'status':'recorded','command':args.command,'workspace':str(workspace)},ensure_ascii=False))
    return 0

if __name__=='__main__':
    try:
        raise SystemExit(main())
    except (OSError,ValueError,KeyError,TypeError,RuntimeError) as error:
        print(json.dumps({'status':'invalid_input','error':str(error)},ensure_ascii=False),file=sys.stderr)
        raise SystemExit(2)
