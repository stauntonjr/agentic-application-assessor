# Pi reference adapter operations

The Pi adapter remains experimental. It maps repository-local policy into Pi without selecting a
model, installing an extension package, providing a sandbox, or claiming independent verifier
identity.

## Tool-call safeguards

`.pi/extensions/context-readiness.ts` requests JSON-schema constrained sampling for the
`harness_questionnaire` tool. OpenAI-compatible servers that honor strict function schemas can then
constrain automatic tool calls to advertised names and arguments. Providers that ignore strict
sampling still receive the ordinary schema.

The extension inspects each `tool_execution_start` before Pi resolves or executes the tool. Calls to
names outside the active tool set increment a consecutive-call counter; any active-tool call resets
it. On the third consecutive unavailable call, the extension records
`harness.invalid-tool-ceiling` in session state and aborts before Pi can preflight a fourth sibling
call. Pi still emits its ordinary not-found result for each of the three unavailable calls; none is
executed.

Run the deterministic offline resource check with:

```bash
make pi-runtime-check
```

When a compatible local model is already serving, exercise real tool calls with:

```bash
python3 tools/pi_tool_probe.py \
  --pi /path/to/pi \
  --provider local-vllm \
  --model MODEL_ID
```

The live probe requires one correct `read` with no extra calls, one strict questionnaire call, a
three-call adversarial ceiling whose results are all explicitly rejected as unavailable, a fresh
zero-tool session, and a continuation with one enabled but unused `read` tool after verified tool
history.

## Empty-tool continuations

Pi 0.84.1 preserves `tools: []` in an OpenAI-compatible continuation when earlier messages contain
tool history and all tools are disabled. Some vLLM servers reject an empty array instead of treating
it like an omitted field. For those endpoints:

- use a fresh session with `--no-tools` when the task requires zero tool authority; or
- as a compatibility tradeoff, continue with one least-authority tool such as `--tools read` and
  explicitly instruct the model not to call it.

The second pattern still grants repository-read authority. A successful inert probe is evidence
about the tested model and prompt, not an enforcement boundary or an equivalent to zero tools.

Do not retry `--no-tools` after the HTTP 400 in the same session and then trust the next model text;
the failed user message remains in history. Start from the pre-failure session branch or a fresh
session instead. This is a Pi/provider compatibility limitation, not a reason to add shell or write
authority.
