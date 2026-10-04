#!/usr/bin/env python3
"""Run online on the intended target OS/Python to fetch pinned wheels and hashes."""
import hashlib,json,subprocess,sys,tempfile,shutil
from pathlib import Path
root=Path(__file__).resolve().parents[1];wheels=root/'wheels';wheels.mkdir(exist_ok=True)
if any(wheels.iterdir()):raise SystemExit('Use an empty wheels directory to prevent stale wheel mixing')
with tempfile.TemporaryDirectory() as tmp:
    dirs=[]
    for version in ['312','313']:
        dst=Path(tmp)/version;dirs.append(dst)
        subprocess.run([sys.executable,'-m','pip','download','--only-binary=:all:','--python-version',version,'--implementation','cp','--abi','cp'+version,'--abi','abi3','--abi','none','--platform','manylinux_2_28_x86_64','--platform','manylinux_2_27_x86_64','--platform','manylinux_2_17_x86_64','--platform','manylinux2014_x86_64','--dest',str(dst),'-r',str(root/'requirements.lock.txt')],check=True)
    common={p.name for p in dirs[0].glob('*.whl')} & {p.name for p in dirs[1].glob('*.whl')}
    for version,dst in zip(['312','313'],dirs):
        for p in dst.glob('*.whl'):
            target=wheels/('shared' if p.name in common else 'python'+version);target.mkdir(exist_ok=True)
            if not (target/p.name).exists():shutil.copy2(p,target/p.name)
hashes={str(p.relative_to(root)):hashlib.sha256(p.read_bytes()).hexdigest() for p in sorted(root.rglob('*')) if p.is_file() and '__pycache__' not in p.parts and '.venv' not in p.parts and p.name!='SHA256SUMS.json'}
(root/'SHA256SUMS.json').write_text(json.dumps(hashes,indent=2)+'\n')
