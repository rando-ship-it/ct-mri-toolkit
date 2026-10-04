# Engineering verification — 2026-10-04

Host: Linux x86-64, glibc 2.39. Actual execution tested on CPython **3.12.14 and 3.13.15**. The latter verifies the Python 3.13 wheel/ABI target; it is not an exact execution test of 3.13.5. Exact package versions are in requirements.lock.txt.

All **12 synthetic checks passed on both interpreters**:

| Check | What was verified |
|---|---|
| CT scaling / distance / display | Known stored values, slope/intercept, physical spacing and window mapping |
| MRI source values | Uncompressed MR pixels remain unchanged without a modality transform |
| Geometry ordering / gaps | Physical positions override filenames/instance numbers; irregular and repeated positions flagged |
| Oblique ordering | Cross-product projection orders an oblique stack correctly |
| ZIP protection | Parent-directory traversal rejected |
| Lossless compression | Exact round trips for RLE, JPEG-LS and JPEG2000 |
| Enhanced transform guard | Shared pixel transforms are refused rather than silently misapplied |
| Full export CLI | All three synthetic CT slices exported under all four HU display presets |
| SimpleITK | Source spacing, physical coordinate and rescaled voxel agree |
| dcm2niix / NiBabel | Synthetic MR conversion creates expected dimensions, values and physical RAS correspondence despite row flipping |
| highdicom | Import succeeds; SEG/SR functionality not tested or implemented |
| Validated volume helper | Every source slice checked against reconstructed pixels/coordinates; source provenance and written NIfTI affine agree |

The initial dcm2niix test could not locate the executable because invoking a venv's Python does not activate its PATH. The test now uses the package-provided binary path; conversion passes on both interpreters. No decoder/converter discrepancy remained in these fixtures.

Not validated: real clinical CT/MRI studies, diagnostic sensitivity/specificity, JPEG baseline/lossy or all vendor encodings, enhanced per-frame geometry, diffusion/time/echo grouping, registration, desktop viewers, segmentation, DICOM SEG/SR, Windows/macOS/ARM/musl/older glibc. Wheel installation and simple cases do not imply universal study support or clinical validation.

The wheel set contains 8 shared distributions and 5 version-specific distributions for each Python. Fresh `install.py` runs on both interpreters selected the correct folders, verified checksums, installed all packages with `--no-index`, and passed all 12 checks. `pip check` also passed in both installed environments.
