# Concurrent native parser isolation

The complete automatic development run exposed a reproducible process crash
when different IFC files were opened concurrently. macOS crash reports identify
`ifcopenshell::instance_data::populate_derived_` and the IFC file-header loader.
A later reproduction identified a second entry through lazy room-geometry
loading. Both failed runs are retained locally. They made zero and one model
attempt respectively; they are failed runs, not accuracy results.

Native extraction, PDF/CAD rendering and the lazy IFC room/stair geometry paths
now execute in bounded child processes. Each task owns its native handles.
The API never receives an IfcOpenShell or PyMuPDF handle. Process failure and
240-second timeout become file errors. Geometry failure withholds the native
answer rather than manufacturing a quantity. Existing pure-data solvers and
all model policies are unchanged.

The PDF isolation also follows the publisher's explicit warning that PyMuPDF
multithreaded use can crash Python:
[PyMuPDF multiprocessing](https://pymupdf.readthedocs.io/en/latest/recipes-multiprocessing.html).

Verification includes concurrent extraction plus preview of four independent
PDFs, simultaneous geometry queries on four generated 4-by-3-metre IFC rooms,
a simulated native process crash, and credential removal from worker environments.
All 378 backend tests passed at the frozen parser revision `190e116`.
The new complete automatic development run uses that immutable application
revision and the production Carbon model policy. The 924-question Saturday
reserve and the released independent reserved-file evaluation are excluded.
