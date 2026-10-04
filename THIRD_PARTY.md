# Third-party distributions

The wheels are unmodified upstream binary distributions obtained through pip. Each wheel includes its own distribution metadata, copyright notices and license files (usually under `.dist-info/licenses` or `.dist-info`). Preserve these files on redistribution. Licenses vary by package and bundled native libraries; this toolkit does not relicense those dependencies. Read each wheel's notices before redistributing under your own project terms.

Included distributions: pydicom, numpy, pillow, pylibjpeg, pylibjpeg-libjpeg, pylibjpeg-openjpeg, pyjpegls, SimpleITK, nibabel, highdicom, dcm2niix, packaging, typing-extensions. The package list and versions in `requirements.lock.txt` are authoritative.

The original scripts, prompt and documentation in this toolkit are provided under the MIT license in LICENSE. No upstream skill source was copied.
