# External reference checks

Accessed 2026-10-04. These checks informed **software design only**. No supplied patient study was available in this workspace for interpretation; no case/dataset/identifier searches or medical diagnostic threshold checks were performed.

| Exact search / open | Why | Sources consulted | Information used |
|---|---|---|---|
| `site.pydicom.github.io pixel data decoding apply modality lut compressed transfer syntax` | Verify scaling and decoder APIs | https://pydicom.github.io/pydicom/stable/reference/pixels.processing.html ; https://pydicom.github.io/pydicom/stable/guides/decoding/decoder_options.html | Use modality LUT/rescale before numerical analysis; keep decoding distinct from display |
| `site.simpleitk.org image physical space origin spacing direction DICOM` | Verify physical coordinate model | https://simpleitk.org/doxygen/v2_5/html/classitk_1_1simple_1_1Image.html | Treat images as physical objects with origin, spacing and direction |
| `site.github.com/rordenlab/dcm2niix releases conversion DICOM` | Check conversion project/release availability | https://github.com/rordenlab/dcm2niix ; https://github.com/rordenlab/dcm2niix/releases | Use dcm2niix as optional conversion tool and check geometry; exact installed version confirmed locally |
| `site.pydicom.github.io/pydicom/stable supported transfer syntaxes pylibjpeg JPEG LS JPEG 2000` | Additional decoder verification | Search returned unrelated results; none used | No effect; consulted official page directly instead |
| `site.slicer.readthedocs.io DICOM loading measurements` | Check viewer suitability | Search returned unrelated results; none used | No effect; consulted official page directly instead |
| Direct open: https://pydicom.github.io/pydicom/stable/guides/user/image_data_handlers.html | Resolve decoder coverage | Official pydicom documentation | Include decoder plugins and independently check decoded output; avoid assuming installation proves fidelity |
| Direct open: https://slicer.readthedocs.io/en/latest/user_guide/modules/dicom.html | Check optional visual QC route | Official Slicer documentation | DICOM import/loading and geometry warnings support optional human QC; application omitted from offline package |
| Direct open: https://simpleitk.readthedocs.io/en/master/link_DicomSeriesReader_docs.html | Check series loading | Official SimpleITK documentation | Series filenames should follow scan direction; compare reconstructed geometry to source |

## Offline implementation notes
These are paraphrased software reminders, not clinical references:
- pydicom decodes supported pixels through available plugins and exposes a separate modality transform. Correctness still needs verification.
- SimpleITK uses physical geometry, ordinarily DICOM LPS; do not confuse array axes with patient axes.
- NIfTI conversions may flip array axes while preserving physical coordinates. Source image references must be retained separately.
- Contrast metadata can be absent in exports. Absence of a tag alone is insufficient to establish lack of contrast.

For a future clinical review, create a fresh general-medical search/reference log tied to independently observed findings. This file does not establish any measurement's clinical normality.
