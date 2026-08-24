#!/usr/bin/env python3
"""Compatibility CLI for the harness-owned Actions supply-chain validator."""

from __future__ import annotations

import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) in sys.path:
    sys.path.remove(str(ROOT))
sys.path.insert(0, str(ROOT))

from harness.runtime.actions_supply_chain import check_workflows, main  # noqa: E402, F401


if __name__ == "__main__":
    sys.exit(main())
