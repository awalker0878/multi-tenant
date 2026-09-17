.PHONY: check route-check packet-lab dns-lab readback-lab terraform-check package-check
check:
	python tools/check_local.py
route-check:
	python tools/route_audit.py examples/wd14-routing.json --output quality/reference_route_checks.json
packet-lab:
	python lab/run_namespace_lab.py --execute
dns-lab:
	python lab/run_dns_lab.py --execute
terraform-check:
	python tools/verify_terraform.py --mock-tests
package-check:
	python tools/check_package.py

readback-lab:
	python lab/run_readback_lab.py --execute
