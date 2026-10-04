#!/usr/bin/env python3
"""Validate a conventional stack against every original slice, then write NIfTI.
No enhanced multiframe, mixed echoes/time, irregular or tilted stacks.
"""
import argparse,json
from pathlib import Path
import numpy as np
import pydicom
import SimpleITK as sitk
from dicom_review import scaled_pixels

def build(index,series_uid,output):
    j=json.loads(Path(index).read_text());groups=[s for s in j['series'] if s['series_uid']==series_uid]
    if len(groups)!=1:raise ValueError('Specify exactly one indexed SeriesInstanceUID')
    group=groups[0];g=group['geometry']
    if g['issues']:raise ValueError('Stack refused: '+ '; '.join(g['issues']))
    if len(g['physical_order'])!=group['objects'] or len(g['physical_order'])<2:raise ValueError('Need at least two conventional image slices, without non-image objects')
    lookup={r['id']:r for r in j['records']};records=[lookup[x] for x in g['physical_order']]
    paths=[r['file'] for r in records]
    reader=sitk.ImageSeriesReader();reader.SetFileNames(paths);image=reader.Execute();array=sitk.GetArrayFromImage(image)
    if array.ndim!=3 or array.shape[0]!=len(records):raise ValueError('Unexpected reconstructed array')
    provenance=[]
    for k,(r,path) in enumerate(zip(records,paths)):
        ds=pydicom.dcmread(path,force=True);_,source=scaled_pixels(ds)
        if source.shape!=array[k].shape or not np.allclose(source,array[k],atol=1e-5,rtol=1e-5):raise ValueError('Source/reconstructed voxel mismatch')
        o=np.array(ds.ImageOrientationPatient,float);s=np.array(ds.PixelSpacing,float);origin=np.array(ds.ImagePositionPatient,float)
        for row,col in [(0,0),(ds.Rows-1,ds.Columns-1)]:
            expected=origin+col*s[1]*o[:3]+row*s[0]*o[3:]
            if not np.allclose(image.TransformIndexToPhysicalPoint((col,row,k)),expected,atol=.01,rtol=0):raise ValueError('Source/reconstructed physical-coordinate mismatch')
        provenance.append({'volume_index_z':k,'source_id':r['id'],'SOPInstanceUID':r.get('SOPInstanceUID'),'InstanceNumber':r.get('InstanceNumber'),'file':path})
    target=Path(output)
    if target.exists() or Path(str(target)+'.sources.json').exists():raise ValueError('Do not overwrite prior outputs')
    target.parent.mkdir(parents=True,exist_ok=True);sitk.WriteImage(image,str(target))
    meta={'series_uid':series_uid,'spacing_mm':image.GetSpacing(),'origin_lps_mm':image.GetOrigin(),'direction_lps':image.GetDirection(),'source_order':provenance,'note':'Validated conventional source stack; derived views are not independent acquisitions. NIfTI uses RAS coordinates; index provenance describes the stored output array.'}
    Path(str(target)+'.sources.json').write_text(json.dumps(meta,indent=2));return meta

if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('index');p.add_argument('--series',required=True);p.add_argument('--output',required=True);a=p.parse_args();meta=build(a.index,a.series,a.output);print(json.dumps({'slices':len(meta['source_order']),'output':a.output}))
