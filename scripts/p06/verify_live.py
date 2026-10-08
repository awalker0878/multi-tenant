#!/usr/bin/env python3
"""Compose the actual P05 owner journey with the P06 execution campaign."""
import importlib.util
from pathlib import Path
import sys
from live_execution import campaign
ROOT=Path(__file__).resolve().parents[2]
sys.path.insert(0,str(ROOT/'scripts/p05'))
spec=importlib.util.spec_from_file_location('p05_live_verification',ROOT/'scripts/p05/verify_live.py')
module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module)
raise SystemExit(module.main(campaign))
