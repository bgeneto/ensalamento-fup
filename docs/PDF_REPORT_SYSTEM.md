# Autonomous Allocation PDF Report Status

Code-accurate status of PDF report generation in the current repository.

This document replaces older wording that implied PDF generation always happens in the default UI flow.

---

## Short Version

PDF generation exists in the codebase, but it is **not currently produced by the autonomous allocation button used in the main Streamlit page**.

Why:

- the page button calls `execute_autonomous_allocation_partial()`
- PDF generation is implemented in `execute_autonomous_allocation()`
- the partial entry point does not attach `pdf_report` or `pdf_filename` to its result

So the feature exists, but it is not wired into the primary UI path at the moment.

---

## Current Runtime Behavior

### Main page behavior

The button in `pages/7_✅_Ensalamento.py` currently calls:

- `OptimizedAutonomousAllocationService.execute_autonomous_allocation_partial(selected_semester)`

That partial result includes:

- mode
- block-group statistics
- split-demand statistics
- execution time

It does **not** include:

- `pdf_report`
- `pdf_filename`

The page still contains code that would store and expose a PDF download if those fields existed, but they are not present in the result returned by the current entry point.

### Full optimized pipeline behavior

The repository still contains a second entry point:

- `OptimizedAutonomousAllocationService.execute_autonomous_allocation()`

That method:

- runs the full optimized pipeline
- generates the PDF with `AutonomousAllocationReportService`
- returns `pdf_report`
- returns `pdf_filename`

So PDF generation is available only when that full entry point is used.

---

## What Is Accurate To Say Today

### Accurate statements

- PDF generation support exists in the repository.
- The full optimized autonomous pipeline can generate a PDF report.
- The current UI button does not use that path.
- The current UI flow therefore does not normally produce a downloadable PDF.

### Inaccurate statements

- "PDF reports are always generated regardless of mode."
- "Running autonomous allocation from the page always produces a PDF."
- "The current autonomous allocation button automatically stores and exposes a PDF report."

---

## Relationship With DEBUG Mode

The old documentation mixed together:

- PDF generation
- debug logs
- JSON debug reports

Current code reality:

- PDF generation belongs to the full optimized pipeline entry point
- partial mode does not generate PDF output
- debug-report generation is optional and also tied to the full optimized flow

So DEBUG mode is not the deciding factor for whether the current page flow yields a PDF. The deciding factor is which service entry point is called.

---

## If The UI Is Switched Back To The Full Pipeline

If the page starts calling:

- `execute_autonomous_allocation()`

then the existing page code can again:

- receive `pdf_report`
- store it in session state
- save it to `data/reports`
- show a download button

That code path already exists in the page, but the current partial result does not provide the required fields.

---

## Recommendation

When documenting the current product behavior, describe PDF reporting like this:

> PDF report generation is implemented for the full optimized autonomous allocation pipeline, but the main UI currently uses the partial allocation pipeline, which does not return PDF output.

That wording matches the code today.
