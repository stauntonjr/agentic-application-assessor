.PHONY: check test compile actions-supply-chain project-check smoke planning-audit challenge-validate challenges recovery-check harness-version product-version harness-lock harness-eval-validate pi-runtime-check plugin-check plugin-sync

check:
	python3 tools/harness_check.py

test:
	python3 -m unittest discover -s tests -v

compile:
	python3 -m compileall -q tools tests

actions-supply-chain:
	python3 tools/check_actions_supply_chain.py

project-check:
	python3 tools/run_quality.py

smoke: check actions-supply-chain compile test project-check challenge-validate recovery-check

planning-audit:
	python3 tools/github_planning.py audit --offline

challenge-validate:
	python3 tools/run_challenges.py

challenges:
	python3 tools/run_challenges.py --run

recovery-check:
	python3 tools/recovery_scenarios.py

harness-version:
	python3 tools/harness_upgrade.py status

product-version:
	python3 tools/product_version.py

harness-lock:
	python3 tools/harness_upgrade.py lock --yes

harness-eval-validate:
	python3 tools/evaluate_harness.py

pi-runtime-check:
	python3 tools/pi_adapter_check.py

plugin-check:
	python3 tools/skill_plugin.py check

plugin-sync:
	python3 tools/skill_plugin.py sync --yes
