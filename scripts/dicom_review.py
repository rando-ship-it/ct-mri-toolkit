#!/usr/bin/env python3
"""Conservative source-DICOM inventory and lossless-resolution PNG export. No diagnosis."""
import argparse
import hashlib
import json
import stat
import zipfile
from pathlib import Path
import numpy as np
import pydicom
from pydicom.pixels import apply_modality_lut
from PIL import Image

TAGS = ['StudyInstanceUID','SeriesInstanceUID','SOPInstanceUID','SOPClassUID','Modality',
        'SeriesNumber','SeriesDescription','InstanceNumber','NumberOfFrames','ImageType',
        'BodyPartExamined','Laterality','ImageLaterality','PatientPosition','Rows','Columns',
        'PixelSpacing','ImagePositionPatient','ImageOrientationPatient','SliceThickness',
        'SpacingBetweenSlices','ContrastBolusAgent','ContrastBolusRoute','ScanningSequence',
        'SequenceVariant','SequenceName','RepetitionTime','EchoTime','InversionTime',
        'MagneticFieldStrength','DiffusionBValue','ConvolutionKernel','KVP',
        'RescaleSlope','RescaleIntercept','RescaleType','WindowCenter','WindowWidth',
        'PhotometricInterpretation','PixelPaddingValue','PixelPaddingRangeLimit']

def value(v):
    if isinstance(v, (list,tuple,pydicom.multival.MultiValue)): return [value(x) for x in v]
    if isinstance(v,(int,float)): return v
    return str(v)

def unpack(inputs, destination, max_bytes=20*1024**3, max_files=100000):
    """Top-level ZIPs only; explicitly supplied directories are scanned recursively."""
    destination=Path(destination); destination.mkdir(parents=True,exist_ok=True)
    files=[]; total=0; count=0
    for idx, raw in enumerate(inputs):
        p=Path(raw)
        if not p.exists(): raise FileNotFoundError(p)
        if p.is_dir():
            files.extend(x for x in sorted(p.rglob('*')) if x.is_file() and not x.is_symlink())
        elif zipfile.is_zipfile(p):
            root=destination/f'archive_{idx:03d}'; root.mkdir(exist_ok=True)
            with zipfile.ZipFile(p) as z:
                seen=set()
                for member in z.infolist():
                    name=member.filename
                    target=(root/name).resolve()
                    if '\\' in name or not target.is_relative_to(root.resolve()) or name.startswith('/'):
                        raise ValueError('Unsafe ZIP path')
                    if stat.S_ISLNK(member.external_attr >> 16): raise ValueError('ZIP symlink rejected')
                    if member.is_dir(): continue
                    if target in seen: raise ValueError('Duplicate ZIP member path')
                    seen.add(target); total+=member.file_size; count+=1
                    if total>max_bytes or count>max_files: raise ValueError('Archive expansion limit exceeded')
                    if target.exists(): raise ValueError('Extraction destination already exists; use a fresh output folder')
                    target.parent.mkdir(parents=True,exist_ok=True)
                    with z.open(member) as src, target.open('wb') as dst:
                        written=0
                        while chunk:=src.read(1024*1024):
                            written+=len(chunk)
                            if written>member.file_size: raise ValueError('Unexpected ZIP expansion')
                            dst.write(chunk)
                    files.append(target)
        else: files.append(p)
    return sorted(set(x.resolve() for x in files))

def geometry(records):
    issues=[]; positions=[]; ref=None; spacing=None; shape=None
    for r in records:
        if int(r.get('NumberOfFrames',1))!=1:
            issues.append('Multiframe geometry requires per-frame reader; not volume-ready'); continue
        try:
            o=np.array(r['ImageOrientationPatient'],float); p=np.array(r['ImagePositionPatient'],float)
            s=np.array(r['PixelSpacing'],float); dims=(r['Rows'],r['Columns'])
            if o.shape!=(6,) or p.shape!=(3,) or s.shape!=(2,) or np.any(s<=0): raise ValueError()
            if not np.isclose(np.linalg.norm(o[:3]),1,atol=1e-4) or not np.isclose(np.linalg.norm(o[3:]),1,atol=1e-4) or abs(o[:3]@o[3:])>1e-4: raise ValueError()
            if ref is None: ref=o; spacing=s; shape=dims
            if not np.allclose(o,ref,atol=1e-4): issues.append('Inconsistent orientation')
            if not np.allclose(s,spacing,atol=1e-5): issues.append('Inconsistent pixel spacing')
            if dims!=shape: issues.append('Inconsistent matrix dimensions')
            positions.append((float(p@np.cross(ref[:3],ref[3:])),r['id'],p))
        except (KeyError,ValueError,TypeError): issues.append('Missing or invalid geometry')
    positions.sort(key=lambda x:(x[0],x[1]))
    gaps=np.diff([x[0] for x in positions]); interval=None
    if len(gaps):
        if np.any(gaps<1e-4): issues.append('Repeated position: duplicate, echo or temporal dimension possible')
        interval=float(np.median(gaps))
        if not np.allclose(gaps,interval,atol=0.05,rtol=.01): issues.append('Irregular projected spacing; not proof of missing slices')
        if interval>0 and len(positions)>1:
            n=np.cross(ref[:3],ref[3:]); delta=np.diff(np.array([x[2] for x in positions]),axis=0)
            if np.any(np.linalg.norm(delta-gaps[:,None]*n,axis=1)>.05): issues.append('In-plane origin shift/tilt; resampling required')
    return {'physical_order':[x[1] for x in positions], 'projected_interval_mm':interval,
            'issues':sorted(set(issues)), 'note':'Grouping and order candidates only; not a validated volume'}

def scaled_pixels(ds):
    if getattr(ds,'SamplesPerPixel',1)!=1: raise ValueError('Only grayscale images supported')
    arr=ds.pixel_array
    if 'PixelValueTransformationSequence' in getattr(ds,'SharedFunctionalGroupsSequence',[pydicom.Dataset()])[0] or any('PixelValueTransformationSequence' in x for x in getattr(ds,'PerFrameFunctionalGroupsSequence',[])):
        raise ValueError('Per-frame/shared pixel transforms require enhanced-object reader')
    return arr, np.asarray(apply_modality_lut(arr,ds),dtype=float)

def display(a, low, high, invert=False):
    if not np.isfinite([low,high]).all() or high<=low: raise ValueError('Invalid display range')
    u=np.clip((a-low)/(high-low),0,1); u=np.where(np.isfinite(u),u,0)
    if invert: u=1-u
    return np.rint(u*255).astype('uint8')

def run(args):
    out=Path(args.output).resolve()
    if out.exists() and any(out.iterdir()): raise ValueError('Use a new empty output directory')
    out.mkdir(parents=True,exist_ok=True)
    files=unpack(args.inputs,out/'extracted')
    records=[]; rejected=[]; groups={}; seen={}; duplicates=[]
    for path in files:
        try:
            ds=pydicom.dcmread(path,stop_before_pixels=True)
        except pydicom.errors.InvalidDicomError:
            try:
                ds=pydicom.dcmread(path,stop_before_pixels=True,force=True)
                if not getattr(ds,'SOPClassUID',None) or not getattr(ds,'SOPInstanceUID',None): raise ValueError('Not identified as DICOM')
            except Exception as e: rejected.append({'file':str(path),'error':type(e).__name__}); continue
        except Exception as e: rejected.append({'file':str(path),'error':type(e).__name__}); continue
        r={k:value(getattr(ds,k)) for k in TAGS if hasattr(ds,k)}
        r.update(id=f'd{len(records):06d}',file=str(path),transfer_syntax=str(getattr(ds.file_meta,'TransferSyntaxUID','unknown')))
        r['sha256']=hashlib.sha256(path.read_bytes()).hexdigest()
        uid=r.get('SOPInstanceUID')
        if uid in seen: duplicates.append({'first':seen[uid],'second':r['id'],'same_bytes':r['sha256']==records[int(seen[uid][1:])]['sha256']})
        elif uid: seen[uid]=r['id']
        r['pixel_status']='not_attempted'
        if args.render and 'Rows' in r and 'Columns' in r:
            try:
                full=pydicom.dcmread(path,force=True); stored,a=scaled_pixels(full)
                frames=a[None] if a.ndim==2 else a
                if frames.ndim!=3: raise ValueError('Unexpected pixel shape')
                pad=np.zeros(stored.shape,dtype=bool)
                if 'PixelPaddingValue' in full:
                    lo=float(full.PixelPaddingValue); hi=float(getattr(full,'PixelPaddingRangeLimit',lo))
                    pad=(stored>=min(lo,hi))&(stored<=max(lo,hi))
                valid=a[~pad & np.isfinite(a)]
                if not valid.size: raise ValueError('No valid pixels')
                ct=r.get('Modality')=='CT'
                hu=ct and r.get('RescaleType','').upper()=='HU' and 'RescaleSlope' in r and 'RescaleIntercept' in r
                r['units']='HU (tag documented)' if hu else 'modality-scaled values; units unverified'
                windows={'lung':(-1000,400),'soft_tissue':(-160,240),'bone':(-500,1500),'brain':(0,80)} if hu else {'percentile':tuple(np.percentile(valid,[.5,99.5]))}
                if args.window: windows={'custom':(args.window[0]-args.window[1]/2,args.window[0]+args.window[1]/2)}
                r['exports']=[]
                for f,frame in enumerate(frames,1):
                    for label,(lo,hi) in windows.items():
                        if hi<=lo: hi=lo+1
                        target=out/'images'/r['id']/f'frame_{f:05d}_{label}.png'; target.parent.mkdir(parents=True,exist_ok=True)
                        Image.fromarray(display(frame,lo,hi,r.get('PhotometricInterpretation')=='MONOCHROME1')).save(target)
                        r['exports'].append({'frame':f,'window':label,'range':[float(lo),float(hi)],'path':str(target.relative_to(out))})
                r['pixel_status']='decoded_and_exported'; r['value_range']=[float(valid.min()),float(valid.max())]
            except Exception as e: r['pixel_status']='failed'; r['pixel_error']=str(e)
        records.append(r)
        key=(r.get('StudyInstanceUID','missing-study'),r.get('SeriesInstanceUID','missing-series'))
        groups.setdefault(key,[]).append(r)
    series=[{'study_uid':k[0],'series_uid':k[1],'objects':len(v),'frames':sum(int(x.get('NumberOfFrames',1)) for x in v),'geometry':geometry([x for x in v if 'Rows' in x]),'ids':[x['id'] for x in v]} for k,v in groups.items()]
    result={'tool_version':'1.0','dicom_objects':len(records),'rejected_files':rejected,'duplicates':duplicates,'series':series,'records':records,'limitations':['No clinical interpretation performed','Exported is not inspected: keep a separate coverage log','No enhanced per-frame geometry or automatic volume reconstruction','Metadata and burned-in pixels may contain identifiers; outputs are sensitive','Nested ZIPs are not extracted; supply them explicitly']}
    (out/'study_index.json').write_text(json.dumps(result,indent=2))
    (out/'coverage_log.csv').write_text('series_uid,source_ids_or_frames_actually_opened,omitted_and_reason,reviewer_notes\n')
    print(json.dumps({'objects':len(records),'series':len(series),'decode_failures':sum(x['pixel_status']=='failed' for x in records),'index':str(out/'study_index.json')}))

if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__); p.add_argument('inputs',nargs='+'); p.add_argument('--output',required=True); p.add_argument('--render',action='store_true'); p.add_argument('--window',nargs=2,type=float,metavar=('CENTER','WIDTH'))
    run(p.parse_args())
