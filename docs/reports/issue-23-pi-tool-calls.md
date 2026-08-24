# Issue #23: Pi tool-call hardening

## Outcome

Issue #23 hardens the experimental Pi adapter before another application dogfood. The running
SparkRun recipe was already correct: vLLM serves `Intel/Qwen3-Coder-Next-int4-AutoRound` with
automatic tool choice and the `qwen3_coder` parser. The defects were in unconstrained automatic
tool names, unbounded recovery after Pi rejected an unknown name, and continuation requests with an
empty tool array.

## Implemented boundary

- `harness_questionnaire` requests preferred JSON-schema constrained sampling. Pi 0.84.1 maps that
  to a strict OpenAI-compatible function definition when the provider supports strict mode.
- The adapter intercepts every attempted tool call, resets on an active name, records an auditable
  session entry, and aborts at three consecutive unavailable names before a fourth sibling call can
  be preflighted.
- `tools/pi_tool_probe.py` reproduces an exclusive correct read, a strict questionnaire call, an
  adversarial invalid-tool ceiling whose calls all return not-found errors, a fresh zero-tool
  session, and a one-read-tool continuation whose setup proves prior tool history.
- Operational guidance keeps zero-tool fresh sessions distinct from continuations that contain
  prior tool history.

## Live evidence collected during implementation

- Direct vLLM requests selected the advertised `read` function and declined a missing shell
  capability, both with ordinary and strict function definitions.
- A clean Pi run called `read` once and returned `# Agent operating contract`.
- With the strict questionnaire tool advertised, Pi used the valid `read` tool in the controlled
  read scenario. The adversarial missing-shell scenario intentionally excluded the questionnaire
  and proves the independent runtime ceiling rather than strict sampling.
- A dedicated strict-sampling lane called `harness_questionnaire` once with the required nullable
  fields and no additional tool call, then returned `QUESTIONNAIRE_SCHEMA_OK`.
- With the strict tool deliberately excluded, an adversarial prompt produced exactly three
  rejected `run_shell_command` calls. Pi recorded `harness.invalid-tool-ceiling`, aborted, settled,
  and executed no command.
- A continuation with tool history and `--no-tools` reproduced vLLM's HTTP 400. A fresh equivalent
  continuation with `--tools read` returned `ONE_INERT_TOOL_CONTINUATION_OK` without calling it.
- A fresh `--no-tools` session returned `FRESH_ZERO_TOOL_OK` with no tool execution; the one-read
  continuation is a tested nonzero-authority compatibility tradeoff, not a zero-tool boundary.

These are implementation-session observations. Final criterion checks, exact candidate identity,
and an independent verdict are recorded in the engineering-loop artifact before publication.

## Candidate checks

- `python3 -m unittest tests.test_pi_adapter_check tests.test_pi_tool_guard -v`: 7 passed.
- `python3 tools/pi_adapter_check.py --pi /home/jrs/.local/share/pi-node/node-v22.23.2-linux-arm64/bin/pi`:
  Pi 0.84.1 loaded every project resource offline and the extension contract passed.
- `python3 tools/pi_tool_probe.py --pi /home/jrs/.local/share/pi-node/node-v22.23.2-linux-arm64/bin/pi --provider local-vllm --model Intel/Qwen3-Coder-Next-int4-AutoRound --timeout 120`:
  all five live scenarios passed; the adversarial lane recorded exactly three rejected calls and
  one ceiling entry, and the fresh zero-tool lane executed no tool.
- `make smoke`: harness check, supply-chain validation, compilation, all 104 unit tests, and the
  provisional template quality boundary passed.

## Residual boundary

The adapter remains experimental. Strict sampling depends on provider support, repository-local
extensions execute with the launching user's authority, Pi does not supply a sandbox or independent
role isolation here, and model-generated research still requires source and verifier gates.
