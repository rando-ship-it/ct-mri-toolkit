#!/usr/bin/env python3
"""Install from bundled wheels without network; do not unpack a venv from another host."""
import hashlib,json,platform,subprocess,sys,venv
from pathlib import Path
root=Path(__file__).resolve().parent
if platform.python_implementation()!='CPython' or sys.version_info[:2] not in ((3,12),(3,13)) or platform.system()!='Linux' or platform.machine() not in ('x86_64','AMD64'):
    raise SystemExit('This wheel bundle targets Linux x86-64 / CPython 3.12 or 3.13. Build matching wheels on your target host; do not force incompatible wheels.')
libc,version=platform.libc_ver()
if libc!='glibc' or tuple(int(x) for x in version.split('.')[:2])<(2,28):
    raise SystemExit('This build requires glibc >= 2.28; musl/older glibc need separate wheels.')
manifest=root/'SHA256SUMS.json'
if not manifest.exists():raise SystemExit('Missing checksum manifest')
for name,digest in json.loads(manifest.read_text()).items():
    path=root/name
    if not path.is_file() or hashlib.sha256(path.read_bytes()).hexdigest()!=digest:raise SystemExit('Checksum failure: '+name)
env=root/'.venv'
if env.exists():raise SystemExit('Existing .venv: remove or move it explicitly before installing')
venv.EnvBuilder(with_pip=True).create(env)
python=env/'bin/python'
specific=root/'wheels'/f'python{sys.version_info.major}{sys.version_info.minor}'
print('Detected CPython '+platform.python_version()+': shared + '+specific.name,flush=True)
subprocess.run([str(python),'-m','pip','install','--no-index','--only-binary=:all:','--find-links',str(root/'wheels/shared'),'--find-links',str(specific),'-r',str(root/'requirements.lock.txt')],check=True)
subprocess.run([str(python),str(root/'tests/self_check.py')],check=True)
print('Offline install and synthetic checks passed. This is not real-study or clinical validation.')
