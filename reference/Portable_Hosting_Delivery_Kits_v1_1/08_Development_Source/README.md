# Build and maintain the developed documents

This is the current v1.1 builder. It changes only the five developed specifications, the root Delivery Map, new development registers and root navigation. It never edits the frozen architecture, prior role guides/templates, workbooks, reference procedure catalogues or native infrastructure.

## Inputs and sources

`author_content.py` contains the reviewed document-development text and public mechanism-source register. It writes `documents.json` and `sources.json`. Edit the Python content source, not the generated JSON, to keep rebuilds consistent. `build_documents.py` creates the six DOCX files with section bookmarks, descriptive relative links, repeated table headers and editable content controls. `build_registers.py` creates the DD treatment register, Q11 reference cards, calculation examples and navigation.

The complete extracted release is the build context: the original reference and role documents supply the target bookmarks. Do not run the new builder in an otherwise empty directory and expect those dependencies to appear.

## Rebuild

From the extracted package root, with the recorded Python dependencies available:

```text
python 08_Development_Source/author_content.py
python 08_Development_Source/build_documents.py
python 08_Development_Source/build_registers.py
python 08_Development_Source/validate_release.py --root .
```

`requirements.txt` records the DOCX-building dependency versions used here. `build_environment.json` records the construction environment. The validator uses Python's standard library and is read-only unless `--output` is supplied.

A rebuild invalidates old DOCX byte fingerprints. Render the changed documents in Word or a suitable document converter and inspect every affected page. Re-run your accessibility review. Only then update the per-file fingerprint and actual page-review result in `07_Quality/v1_1/visual_review.json`. Do not set a review flag without examining the output. A different renderer can change line wrapping or pagination.

```text
python 08_Development_Source/validate_release.py --root . --output 07_Quality/v1_1/validation_report.json
python 08_Development_Source/package_release.py --root . --archive ../Portable_Hosting_Architecture_Engineering_Implementation_Kits_v1_1.zip
```

The packaging command first checks current local validation. It creates a fresh manifest/checksum list and archive; it does not invent or rerun manual visual reviews. Keep its output archive outside the release directory.

## Limits

These scripts create and check documents, links, identity/count parity and illustrative arithmetic. They do not provision a switch or hosting platform, execute the CT or Q11 procedures, verify a product support claim, run workbook formulas, or authorize a change.

The retained `source/` directory and `06_Tools/check_package.py` belong to v1.0 and are historical construction/check material. Running them over this release can overwrite or mischaracterize v1.1 artifacts. The original optional plan-metadata reviewer remains unchanged and offline.
