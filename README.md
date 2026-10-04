# CT / MRI review kit

A small, auditable toolbox plus an independent-review prompt. No patient images, diagnosis model, pretrained weights or case lookup. Use it with an agent that can run Python **and actually inspect images**.

## Easiest use
Upload this ZIP alongside the study archives and paste `PROMPT.md` into the agent's instructions. Ask it to unzip the **toolkit separately from the patient study**, read this README, install locally, run the checks and then review the study. No internet is needed for the included installation on the supported platform. The installer automatically selects `wheels/shared` plus `wheels/python312` or `wheels/python313`; you do not choose versions manually.

```bash
python3 install.py
.venv/bin/python scripts/dicom_review.py /path/study1.zip /path/study2.zip --output /path/new_review --render
```

Every conventional grayscale image is exported at native matrix resolution with source provenance in `study_index.json`. CT with documented HU rescale receives lung, soft-tissue, bone and brain display presets. Other images receive a per-object percentile display range; this does **not** permit intensity comparisons between MRI sequences. Set `--window CENTER WIDTH` for a fixed display range across images when needed. Exports are 8-bit display images; quantitative measurements always read original DICOM. Images are in stored orientation, not automatically radiological orientation; verify DICOM orientation before identifying side.

The agent must open images, maintain `coverage_log.csv`, verify candidates and use the two report sections in the prompt. Exporting all images does not mean reviewing them. This kit never creates a clinical report automatically. Large CT studies require paging/full-resolution inspection; do not claim complete review after sampling.

## Included and checked
Core: pydicom, NumPy, Pillow and JPEG/JPEG-LS/JPEG2000 decoder packages. Optional volume tools included: SimpleITK, dcm2niix and NiBabel. highdicom is included for optional higher-level DICOM handling. Exact versions are pinned in `requirements.lock.txt`; tests and results are in `TEST_RESULTS.md`. Wheels retain their upstream license metadata; see `THIRD_PARTY.md`.

This offline build targets **CPython 3.12 or 3.13, Linux x86-64, glibc 2.28 or newer** (some bundled wheels require it), with Python's venv/ensurepip available. It is not a portable Python runtime. macOS, Windows, ARM and other Python versions need their own compatible wheels; simply uploading this ZIP will not fix an incompatible agent environment. A sandbox that cannot execute Python or open images cannot use this workflow for interpretation.

On an internet-connected build host, `python scripts/build_wheels.py` downloads both supported Python wheel sets and rebuilds checksums. For other targets, remove the old wheels, resolve compatible versions, adapt the installer platform check and rerun all checks before calling that build supported. Do not distribute a copied virtual environment.

## Measurements
Single-frame source-image distances and rectangular ROI summaries:

```bash
.venv/bin/python scripts/measure.py /path/image.dcm --points 10 20 30 40
.venv/bin/python scripts/measure.py /path/image.dcm --roi 10 20 30 40
```

Coordinates are zero-based **row,column** in the original matrix. Distance uses DICOM LPS coordinates in mm. ROI bounds are start-inclusive/end-exclusive; padding is excluded. HU is labeled only when CT tags document it. These are numerical tools; the operator selects the correct landmarks/ROI, checks image calibration, artifacts and partial volume, and verifies any applicable clinical reference. No screenshot measurement, automatic lesion measurements or built-in normal thresholds.

## Volumes and human QC

For a conventional stack without geometry warnings, `volume.py` compares reconstructed voxels and physical coordinates against **every source slice**, then writes a NIfTI and exact source-order sidecar. It refuses irregular, tilted, multiframe or mixed-position stacks. It does not register acquisitions or automatically resolve echo/time dimensions.

```bash
.venv/bin/python scripts/volume.py /path/new_review/study_index.json --series ORIGINAL_SERIES_UID --output /path/volume.nii.gz
```
For conventional, coherent source series, SimpleITK can load a geometry-sorted stack. Do not use filenames as slice order. Use dcm2niix only on isolated compatible acquisitions, retain its logs and JSON sidecars, and compare source geometry and values before using conversions. Example after activating the environment:

```bash
source .venv/bin/activate
dcm2niix -z y -b y -ba y -o /path/new_nifti /path/isolated_dicom_series
```

The NIfTI converter may flip array axes while preserving physical coordinates. Keep source-DICOM mapping; NIfTI slice indices are not DICOM image numbers. SimpleITK uses LPS; NiBabel/NIfTI commonly use RAS. Conversion does not establish correct handling of every vendor/enhanced object.

3D Slicer is an optional external desktop viewer for synchronized MPR and human verification; it is **not bundled or tested here**. GPU models, MONAI, TotalSegmentator and Orthanc are omitted to keep this kit small. Add a specific validated capability only when needed.

## Boundaries
Enhanced multiframe per-frame geometry/transform, temporal/echo/diffusion grouping, automatic registration, segmentation, annotations, PACS and DICOM SEG/SR are not implemented. Multiframe grayscale pixels without special transforms may export, but are not volume-ready. Unsupported pixel transforms/decoders produce explicit failures. Missing contrast fields do not establish absence of contrast. Geometry checks flag concerns rather than prove completeness. DICOMDIR and non-image objects may be inventoried without rendering. Nested ZIPs must be supplied explicitly. If the installer or an optional tool fails, follow the recovery instructions in PROMPT.md and document the narrower available review; never infer findings from unreadable pixels.

No clinical study is included or was available for validation during this build. Passing synthetic tests is engineering evidence, not diagnostic validation. Outputs remain sensitive: filenames, descriptions, UIDs and burned-in pixel text can identify a patient even though explicit patient-name/ID fields are omitted. Do not publish study inputs or review outputs in a public repository.

## Sharing simply
Use the ZIP for offline agents. For long-term distribution, put the source-only kit in a GitHub repository and attach platform-specific offline ZIPs to releases; keep the large wheels out of git history. An agent without internet still needs the uploaded ZIP. The versioned public distribution is https://github.com/rando-ship-it/ct-mri-toolkit/releases/tag/v1.0.0 . Use the release asset for offline installation; the source archive alone does not contain wheels.
