#!/usr/bin/env python3
"""Synthetic checks; no patient data, no diagnostic validation."""
import json,sys,tempfile,unittest,zipfile,subprocess,shutil
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'scripts'))
import numpy as np
import pydicom
from pydicom.dataset import FileDataset,FileMetaDataset
from pydicom.uid import generate_uid,ExplicitVRLittleEndian,CTImageStorage,MRImageStorage,JPEGLSLossless,JPEG2000Lossless,RLELossless
from dicom_review import geometry,scaled_pixels,unpack,display
from measure import point

def fixture(path,modality='CT',z=0,instance=1,series=None):
    meta=FileMetaDataset();meta.TransferSyntaxUID=ExplicitVRLittleEndian;meta.MediaStorageSOPClassUID=CTImageStorage if modality=='CT' else MRImageStorage;meta.MediaStorageSOPInstanceUID=generate_uid()
    ds=FileDataset(str(path),{},file_meta=meta,preamble=b'\0'*128);ds.SOPClassUID=meta.MediaStorageSOPClassUID;ds.SOPInstanceUID=meta.MediaStorageSOPInstanceUID
    ds.StudyInstanceUID='1.2.826.0.1.3680043.8.498.1';ds.SeriesInstanceUID=series or generate_uid();ds.Modality=modality;ds.SeriesNumber=1;ds.InstanceNumber=instance;ds.SeriesDescription='SYNTHETIC TEST ONLY'
    ds.Rows=64;ds.Columns=64;ds.PixelSpacing=[.7,.5];ds.SliceThickness=2;ds.ImageOrientationPatient=[1,0,0,0,1,0];ds.ImagePositionPatient=[0,0,z]
    ds.SamplesPerPixel=1;ds.PhotometricInterpretation='MONOCHROME2';ds.BitsAllocated=16;ds.BitsStored=16;ds.HighBit=15;ds.PixelRepresentation=0
    a=np.arange(4096,dtype=np.uint16).reshape(64,64);ds.PixelData=a.tobytes()
    if modality=='CT': ds.RescaleSlope=2;ds.RescaleIntercept=-1024;ds.RescaleType='HU'
    ds.save_as(path,enforce_file_format=True);return ds,a

class Checks(unittest.TestCase):
    def setUp(self): self.tmp=tempfile.TemporaryDirectory();self.root=Path(self.tmp.name)
    def tearDown(self): self.tmp.cleanup()
    def test_ct_scaling_and_distance(self):
        ds,a=fixture(self.root/'ct.dcm');raw,v=scaled_pixels(ds);np.testing.assert_array_equal(v,a.astype(float)*2-1024)
        self.assertAlmostEqual(np.linalg.norm(point(ds,10,20)-point(ds,0,0)),np.hypot(7,10));self.assertEqual(display(np.array([-1000,0,1000]),-1000,1000).tolist(),[0,128,255])
    def test_mri_unscaled(self):
        ds,a=fixture(self.root/'mr.dcm','MR');np.testing.assert_array_equal(scaled_pixels(ds)[1],a)
    def test_highdicom_import(self):
        import highdicom
        self.assertTrue(highdicom.__version__)
    def test_physical_order_and_gap(self):
        r=[dict(id=str(i),Rows=64,Columns=64,PixelSpacing=[.7,.5],ImagePositionPatient=[0,0,z],ImageOrientationPatient=[1,0,0,0,1,0],InstanceNumber=99-i) for i,z in enumerate([4,0,2])]
        g=geometry(r);self.assertEqual(g['physical_order'],['1','2','0']);self.assertEqual(g['issues'],[])
        r[0]['ImagePositionPatient'][2]=8;self.assertTrue(any('Irregular' in s for s in geometry(r)['issues']))
        r[0]['ImagePositionPatient'][2]=2;self.assertTrue(any('Repeated' in s for s in geometry(r)['issues']))
    def test_oblique_geometry(self):
        o=[1,0,0,0,2**-.5,2**-.5];n=np.cross(o[:3],o[3:]);r=[dict(id=str(i),Rows=64,Columns=64,PixelSpacing=[.7,.5],ImagePositionPatient=(n*z).tolist(),ImageOrientationPatient=o) for i,z in enumerate([4,0,2])]
        self.assertEqual(geometry(r)['physical_order'],['1','2','0'])
    def test_zip_path_rejected(self):
        z=self.root/'bad.zip'
        with zipfile.ZipFile(z,'w') as f:f.writestr('../escape','bad')
        with self.assertRaises(ValueError):unpack([z],self.root/'out')
    def test_compressed_lossless(self):
        for syntax in [RLELossless,JPEGLSLossless,JPEG2000Lossless]:
            with self.subTest(syntax=str(syntax)):
                ds,a=fixture(self.root/'source.dcm');ds.compress(syntax);path=self.root/(str(syntax)+'.dcm');ds.save_as(path,enforce_file_format=True);np.testing.assert_array_equal(pydicom.dcmread(path).pixel_array,a)
    def test_enhanced_transform_refused(self):
        ds,_=fixture(self.root/'enh.dcm');fg=pydicom.Dataset();fg.PixelValueTransformationSequence=[pydicom.Dataset()];ds.SharedFunctionalGroupsSequence=[fg]
        with self.assertRaises(ValueError):scaled_pixels(ds)
    def test_cli_all_images(self):
        src=self.root/'study';src.mkdir();uid=generate_uid()
        for i,z in enumerate([4,0,2]):fixture(src/f'{i}.dcm',z=z,instance=3-i,series=uid)
        out=self.root/'out';script=Path(__file__).resolve().parents[1]/'scripts/dicom_review.py'
        subprocess.run([sys.executable,str(script),str(src),'--output',str(out),'--render'],check=True,capture_output=True)
        j=json.loads((out/'study_index.json').read_text());self.assertEqual(j['dicom_objects'],3);self.assertTrue(all(r['pixel_status']=='decoded_and_exported' for r in j['records']));self.assertEqual(len(list(out.rglob('*.png'))),12)
    def test_simpleitk_geometry_values(self):
        import SimpleITK as sitk
        uid=generate_uid();paths=[]
        for z in [0,2,4]:p=self.root/f'{z}.dcm';fixture(p,z=z,series=uid);paths.append(str(p))
        reader=sitk.ImageSeriesReader();reader.SetFileNames(paths);image=reader.Execute()
        np.testing.assert_allclose(image.GetSpacing(),[.5,.7,2]);np.testing.assert_allclose(image.TransformIndexToPhysicalPoint((20,10,1)),[10,7,2]);self.assertEqual(float(sitk.GetArrayFromImage(image)[0,0,0]),-1024)
    def test_validated_volume_provenance(self):
        from volume import build
        import nibabel as nib
        src=self.root/'source';src.mkdir();uid=generate_uid()
        for i,z in enumerate([4,0,2]):fixture(src/f'{i}.dcm',z=z,instance=3-i,series=uid)
        out=self.root/'out';script=Path(__file__).resolve().parents[1]/'scripts/dicom_review.py'
        subprocess.run([sys.executable,str(script),str(src),'--output',str(out)],check=True,capture_output=True)
        target=self.root/'volume.nii.gz';meta=build(out/'study_index.json',uid,target)
        self.assertEqual([x['InstanceNumber'] for x in meta['source_order']],[2,1,3])
        image=nib.load(target);np.testing.assert_allclose(image.affine@np.array([20,10,1,1]),[-10,-7,2,1],atol=1e-5)
        self.assertEqual(float(image.get_fdata()[20,10,1]),2*(10*64+20)-1024)
    def test_dcm2niix_mri_conversion(self):
        import nibabel as nib
        import dcm2niix
        exe=str(dcm2niix.bin_path);self.assertTrue(Path(exe).is_file())
        src=self.root/'mr';src.mkdir();out=self.root/'nifti';out.mkdir();uid=generate_uid()
        for z in [0,2,4]:fixture(src/f'{z}.dcm','MR',z=z,series=uid)
        p=subprocess.run([exe,'-z','n','-b','y','-o',str(out),str(src)],capture_output=True,text=True)
        self.assertEqual(p.returncode,0,p.stdout+p.stderr);files=list(out.glob('*.nii'));self.assertEqual(len(files),1,p.stdout)
        im=nib.load(files[0]);self.assertEqual(im.shape,(64,64,3));self.assertEqual(float(im.get_fdata().min()),0);self.assertEqual(float(im.get_fdata().max()),4095)
        # dcm2niix flips rows; compare physical points/values through affine in RAS.
        data=im.get_fdata()
        for k in range(3):
            xyz=im.affine@np.array([20,10,k,1]);lps=xyz[:3]*[-1,-1,1]
            row=int(round(lps[1]/.7));col=int(round(lps[0]/.5))
            self.assertEqual(float(data[20,10,k]),float(row*64+col));self.assertAlmostEqual(lps[2],k*2)

if __name__=='__main__':unittest.main(verbosity=2)
