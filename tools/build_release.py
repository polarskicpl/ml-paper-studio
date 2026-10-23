#!/usr/bin/env python3
"""Build standalone-skill and portable-plugin ZIPs using only repository files."""
import hashlib
import json
from pathlib import Path
import zipfile

root=Path(__file__).resolve().parents[1]
version=json.loads((root/'plugin.json').read_text())['version']
skill=root/'skills/ml-paper-studio'
dist=root/'dist'
dist.mkdir(exist_ok=True)

def pack(target, entries):
    expected={}
    with zipfile.ZipFile(target,'w',compression=zipfile.ZIP_DEFLATED,compresslevel=9) as archive:
        for name,path in sorted(entries):
            if path.is_symlink() or not path.resolve().is_relative_to(root):
                raise ValueError('Release inputs must be regular files inside the repository')
            data=path.read_bytes()
            info=zipfile.ZipInfo(name,date_time=(1980,1,1,0,0,0))
            info.compress_type=zipfile.ZIP_DEFLATED
            info.external_attr=0o100644 << 16
            archive.writestr(info,data)
            expected[name]=hashlib.sha256(data).hexdigest()
    with zipfile.ZipFile(target) as archive:
        assert archive.testzip() is None
        assert {name:hashlib.sha256(archive.read(name)).hexdigest() for name in archive.namelist()}==expected
    return hashlib.sha256(target.read_bytes()).hexdigest()+'  '+target.name

skill_files=[p for p in skill.rglob('*') if p.is_file() and '__pycache__' not in p.parts]
hashes=[pack(dist/('ml-paper-studio-skill-v'+version+'.zip'),
             [('ml-paper-studio/'+p.relative_to(skill).as_posix(),p) for p in skill_files])]
plugin_files=[root/name for name in ['plugin.json','LICENSE','README.md','README.zh-CN.md','CHANGELOG.md','docs/VALIDATION.md']]
plugin_files += [p for p in (root/'assets').rglob('*') if p.is_file()]
plugin_files += skill_files
hashes.append(pack(dist/('ml-paper-studio-plugin-v'+version+'.zip'),
                   [(p.relative_to(root).as_posix(),p) for p in plugin_files]))
(dist/'SHA256SUMS').write_text('\n'.join(hashes)+'\n')
print(json.dumps({'version':version,'archives':hashes,'output_directory':str(dist)},ensure_ascii=False),flush=True)
