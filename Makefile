.PHONY: test repo-check unit test-ansible test-terraform test-all labs catalog
PYTHON ?= python

test: repo-check unit
repo-check:
	$(PYTHON) scripts/check_repository.py
unit:
	$(PYTHON) tools/check_local.py
test-ansible:
	$(PYTHON) scripts/verify_ansible.py
test-terraform:
	$(PYTHON) tools/verify_terraform.py --mock-tests
test-all: test test-ansible test-terraform
labs:
	$(PYTHON) lab/run_readback_lab.py --execute
	$(PYTHON) lab/run_dns_lab.py --execute
	$(PYTHON) lab/run_namespace_lab.py --execute
catalog:
	$(PYTHON) scripts/catalog_artifacts.py
