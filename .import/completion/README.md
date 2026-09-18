# Temporary corrective-source transport

This directory holds a checksum-bound, lossless import of reviewed documentation source and four historical Word originals that are absent from the current repository branch. It is not executable application code and is not production configuration.

The one-time import must verify the full compressed bundle, all content objects, exact original document digests and repository-relative paths before writing. No decoded program is executed by the decoder. Normal source generation and tests run as separately reviewed steps on this private corrective branch.

The directory and temporary write-enabled import workflow must be removed before merging to main. Final verification workflows have read-only repository permission and no infrastructure credentials. The import does not grant architectural acceptance or native service readiness.
