# Construction sources

These files construct the proposed delivery-kit records and publications. They are not native infrastructure deployment modules. Never rebuild inside an edited project copy: the generators overwrite templates and reference starter records. Use an isolated duplicate of the extracted release.

## Dependencies

Python 3.11 or later is the reference language environment. Word construction uses python-docx and lxml. Spreadsheet construction uses artifact_tool, available in the authoring environment; this package does not vendor that library or promise that it is installed on the recipient machine. The two read-only utilities under ../06_Tools use only the Python standard library.

## Rebuilding in a separate copy

From that copy's root, run:

```console
python source/build_architecture.py
python source/build_engineering.py
python source/build_implementation.py
python source/build_runbooks.py
python source/build_workbooks.py
python source/build_navigation.py
python 06_Tools/check_package.py --skip-manifest
```

The frozen v1.4 source documents and registers must remain at their relative paths. catalogue.py generates the common proposed kit catalogue; it does not modify the frozen reference files. The document generators use doc_engine.py. The workbook generator reads the resulting kit catalogue and exports all three workbooks.

After any rebuild, render and visually inspect every changed Word document, review the workbooks and formulas, and rerun the local tool tests. Generate a new quality record and release manifest rather than retaining old checksums or claiming old tests validate modified files. Do not replace an existing authorization or test result with a generated starter value.

Rendering tools, installed fonts and platform versions can affect pagination and binary output. Exact byte-identical or cross-environment publishing reproducibility has not been certified. No font binaries are included.
