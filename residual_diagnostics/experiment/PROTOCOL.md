# v13 residual CPU diagnostics (post-hoc selection)

Four cases were selected because v11 explicitly left their deeper claims untested:
Django13568 import NameError, sklearn25102 default branch/value casting,
Astropy13236 warning-before-behavior, and xarray6744 Dask skips.
These cases are post-hoc, not a population accuracy sample or independent labels.

Copy full pinned source from preserved v11, preserving critical source/test bytes
and native extensions. Never edit old sources/environments. Django's fourth tree
adds only a missing models import, a diagnostic intervention rather than the
archived candidate. Base/candidate/developer stay unchanged. Witnesses test
single/multi/conditional uniqueness under both authentication backends, default
and pandas StandardScaler plus PCA, structured ndarray type/ECSV roundtrip,
and centered rolling iteration for NumPy/Dask with default/min_periods1.

Replay Django selected official targets in four trees. Replay Astropy official
targets in three trees under original warnings, then separately with FutureWarning
ignored to reach behavioral assertions. Do not replace original warning-policy
results with amended-policy results. Replay xarray's same whole official rolling
function with pinned Dask2022.9.2 in a separate dependency target. Newly executed
Dask cases are not claimed as prior executed passes. Skip/collection/timeout and
instrumentation errors remain explicit. At most four single-threaded CPU workers.
No original native-model inference, LLM calls, GPU jobs or new human responses.
