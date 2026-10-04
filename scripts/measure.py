#!/usr/bin/env python3
"""Source-image distance / rectangular ROI; single-frame grayscale only."""
import argparse,json
import numpy as np
import pydicom
from dicom_review import scaled_pixels

def point(ds,row,col):
    o=np.asarray(ds.ImageOrientationPatient,float); s=np.asarray(ds.PixelSpacing,float)
    if o.shape!=(6,) or s.shape!=(2,) or np.any(s<=0) or not np.isclose(o[:3]@o[3:],0,atol=1e-4) or not np.allclose([np.linalg.norm(o[:3]),np.linalg.norm(o[3:])],1,atol=1e-4): raise ValueError('Invalid geometry')
    if not(0<=row<ds.Rows and 0<=col<ds.Columns): raise ValueError('Point outside image')
    return np.asarray(ds.ImagePositionPatient,float)+col*s[1]*o[:3]+row*s[0]*o[3:]

if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('dicom');p.add_argument('--points',nargs=4,type=float,metavar=('R1','C1','R2','C2'));p.add_argument('--roi',nargs=4,type=int,metavar=('R0','C0','R1','C1'));a=p.parse_args()
    ds=pydicom.dcmread(a.dicom,force=True)
    if int(getattr(ds,'NumberOfFrames',1))!=1: raise ValueError('Enhanced/multiframe measurements unsupported')
    result={'SOPInstanceUID':str(ds.SOPInstanceUID),'SeriesInstanceUID':str(ds.SeriesInstanceUID),'InstanceNumber':str(getattr(ds,'InstanceNumber','unknown')),'coordinate_convention':'zero-based row,column; LPS mm'}
    if a.points:
        x=point(ds,*a.points[:2]);y=point(ds,*a.points[2:]);result.update(distance_mm=float(np.linalg.norm(y-x)),points_lps_mm=[x.tolist(),y.tolist()])
    if a.roi:
        r0,c0,r1,c1=a.roi
        if not(0<=r0<r1<=ds.Rows and 0<=c0<c1<=ds.Columns): raise ValueError('ROI outside image')
        raw,v=scaled_pixels(ds);mask=np.isfinite(v)
        if 'PixelPaddingValue' in ds:
            lo=float(ds.PixelPaddingValue);hi=float(getattr(ds,'PixelPaddingRangeLimit',lo)); mask&=~((raw>=min(lo,hi))&(raw<=max(lo,hi)))
        roi=v[r0:r1,c0:c1][mask[r0:r1,c0:c1]]
        if not roi.size: raise ValueError('Empty ROI after padding exclusion')
        hu=ds.Modality=='CT' and str(getattr(ds,'RescaleType','')).upper()=='HU' and 'RescaleSlope' in ds and 'RescaleIntercept' in ds
        result['roi']={'bounds':a.roi,'count':int(roi.size),'mean':float(roi.mean()),'sd':float(roi.std()),'min':float(roi.min()),'max':float(roi.max()),'units':'HU (tag documented)' if hu else 'modality-scaled; units unverified'}
    if not a.points and not a.roi: p.error('Supply --points or --roi')
    print(json.dumps(result,indent=2))
