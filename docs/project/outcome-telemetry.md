# Outcome telemetry

Outcome telemetry is optional, local, and content-free. It summarizes a recorded engineering loop
without collecting prompts, responses, messages, transcripts, hidden reasoning, secrets,
credentials, API keys, or token values. The tool makes no network calls and does not read provider
billing or organization data.

## Metric contract

| Metric | Definition | Default evidence |
|---|---|---|
| `human_corrections` | Explicit count of human-directed corrections attributed to this loop at the observation time. | Unavailable until supplied. Zero must be supplied deliberately. |
| `retries` | Additional attempts actually started within each loop revision; attempt one is not a retry. | Derived from the loop record. |
| `escaped_defects` | Explicit count of defects attributed to the accepted change and discovered after its acceptance boundary by the observation time. | Unavailable until reviewed and supplied. Zero must be supplied deliberately. |
| `acceptance_pass_rate` | Passed active acceptance criteria divided by all active, unwaived criteria. | Derived only for a terminal loop; unavailable while work is in progress. |
| `cycle_time` | Sum of explicit, non-overlapping active-work intervals inside the loop wall-clock boundary. | Unavailable until intervals are supplied. |
| `elapsed_time` | Wall-clock seconds from loop start to loop finish. | Derived for a finished loop; unavailable while it is open. |
| `accepted_change_cost` | One explicitly supplied total attributed to a reported accepted change, in USD, person-minutes, or compute-seconds. | Unavailable until supplied; unlike units are never combined. |

These are harness-loop measures. `cycle_time` and `elapsed_time` are not DORA change lead time,
which uses a commit-to-production boundary.

Every measurement has one origin:

- `locally-measured`: counted or calculated from local evidence;
- `provider-reported`: copied from an explicit provider receipt or usage record;
- `inferred`: a disclosed manual estimate;
- `unavailable`: not collected, never silently treated as zero.

The bounded `method` records how that origin was obtained. The validator rejects incompatible
pairs, such as an unavailable value labeled with a local loop-record method.

## Create a summary

With no input file, only values derivable from the loop record are available. Output goes to
stdout and no telemetry directory is created:

```bash
python3 tools/loop_telemetry.py summarize --run RUN_ID
```

Optional observations use the strict schema in `harness/schemas/telemetry-input.schema.json`:

```json
{
  "schema_version": "1.0",
  "run_id": "RUN_ID",
  "observed_at": "2026-08-24T12:00:00Z",
  "human_corrections": {
    "value": 2,
    "origin": {"kind": "locally-measured", "method": "human-count"}
  },
  "escaped_defects": {
    "value": 0,
    "origin": {"kind": "locally-measured", "method": "human-count"}
  },
  "active_intervals": [
    {"started_at": "2026-08-23T10:00:00Z", "ended_at": "2026-08-23T10:30:00Z"}
  ],
  "accepted_change_cost": {
    "value": 18,
    "unit": "person-minute",
    "origin": {"kind": "inferred", "method": "manual-estimate"}
  }
}
```

`observed_at` is optional and defaults to the terminal timestamp, or the command's observation
time for an open loop. Supply it for a later retrospective observation; it cannot predate the loop
boundary being observed.

Run with an explicit input:

```bash
python3 tools/loop_telemetry.py summarize \
  --run RUN_ID \
  --input /path/to/telemetry-input.json
```

Writing is also explicit and restricted to the ignored local telemetry directory:

```bash
python3 tools/loop_telemetry.py summarize \
  --run RUN_ID \
  --input /path/to/telemetry-input.json \
  --output .harness/telemetry/RUN_ID.json
```

The tool refuses path escapes and symlink traversal. It does not copy or retain the raw input.
Written summary retention and deletion remain the caller's responsibility.

## Aggregate summaries

The aggregate command validates every imported summary before reading its measurements:

```bash
python3 tools/loop_telemetry.py aggregate \
  .harness/telemetry/run-a.json \
  .harness/telemetry/run-b.json
```

The result omits run identifiers and source inputs. It reports available/unavailable counts,
origin counts, and count/sum/minimum/maximum within each compatible unit. It does not compute
percentiles, correlate repositories or people, enforce a minimum cohort, write automatically, or
export anywhere.

This output is only the schema boundary for a future organization-wide reporting project. Before
such a project ingests it, define a threat model, minimum cohort size, access controls, retention
and deletion policy, cross-repository identity rules, and consent/notice requirements.

## Privacy and retention defaults

The enforced defaults in `harness/telemetry.json` are:

- disabled unless the CLI is invoked explicitly;
- stdout output unless an allowed local output is requested;
- no prompt, response, message, content, transcript, reasoning, secret, credential, API-key, or
  token fields;
- no raw-input retention;
- caller-managed retention for explicitly written summaries;
- no organization export and no automatic provider access.

These defaults minimize collection; they do not replace repository access control, filesystem
security, or a future organization's privacy review.
