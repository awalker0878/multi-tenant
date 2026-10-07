"""Real PostgreSQL fixture shared with the owning Lifecycle tests; no in-memory substitute."""
import importlib.util
from pathlib import Path

spec = importlib.util.spec_from_file_location('p07_lifecycle_postgres', Path(__file__).resolve().parents[2] / 'services/lifecycle/tests/conftest.py')
module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)
postgres = module.postgres
database = module.database
