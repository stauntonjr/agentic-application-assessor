# Application assessment

- Tool: `agentic-application-assessor 0.1.0`
- Report schema: `1.0`
- Target: `macro-technical-pulse` at `1f06504d850d1160bef9fa6228c3ebdc4e8f02ae`
- Branch: `(detached)`
- Dirty outer worktree: `no`
- State identity: `sha256:f88420a4169764cdf464b0d286cf7ec57e80d5f17e65706c833e41831fe1581f`
- Agentic Repo Auditor artifact: `macro-technical-pulse.auditor-report.json`; tool `0.1.0`; schema `1.2`; sha256 `93505fb1c11f7675b155355a2ad9119d68ad5a793b2de7a7e10da31a937b097a`

## Executive findings

- **application.audience** [human-declared; supported]: Stakeholders: Jack Rory Staunton, application maintainers, economic and market data researchers, feature-engineering and model developers, model validators, independent risk reviewers
- **application.purpose** [human-declared; supported]: Capture and gather economic and market data streams, store them for feature engineering and machine-learning price-prediction models, deploy trained models on live streams, and provide visualization of the collected data, engineered features, signals, and predictions. Technical-response measurement may later analyze price sensitivity to external signals, but it is not the application's primary purpose.

## Evidence coverage

| Kind | Count |
|---|---:|
| documentation | 27 |
| entrypoint | 2 |
| imported-auditor-finding-evidence | 15 |
| imported-auditor-findings | 13 |
| manifest | 1 |
| test | 4 |

## Contradictions

- None detected at the inspected boundary.

## Unknowns and limits

- **unknown.context.components** [unavailable] `macro-technical-pulse.context.json#/components`: No accepted context declares application components.
- **unknown.context.data-assets** [unavailable] `macro-technical-pulse.context.json#/data_assets`: No accepted context declares data assets and movement.
- **unknown.context.quality-scenarios** [unavailable] `macro-technical-pulse.context.json#/quality_scenarios`: No accepted context declares decision-driving quality scenarios.
- **unknown.context.workflows** [unavailable] `macro-technical-pulse.context.json#/workflows`: No accepted context declares important runtime workflows.
- **unknown.model-synthesis** [unavailable] `tool-policy:adr-0008#decision`: Model synthesis is unavailable because the canonical v0.1 core is model-free.
- **unknown.production-topology** [unavailable] `tool-policy:adr-0008#decision`: Production topology is unavailable because live infrastructure and network access are outside the v0.1 trust boundary.
- **unknown.runtime-behavior** [unavailable] `tool-policy:adr-0008#decision`: Runtime behavior is unavailable because target execution is outside the v0.1 trust boundary.
- **unknown.static.deployment** [unavailable] `target:sha256:f88420a4169764cdf464b0d286cf7ec57e80d5f17e65706c833e41831fe1581f#inventory/deployment`: Static inventory found no recognized deployment evidence.
- **unknown.static.interface** [unavailable] `target:sha256:f88420a4169764cdf464b0d286cf7ec57e80d5f17e65706c833e41831fe1581f#inventory/interface`: Static inventory found no recognized interface evidence.

## Evidence index

- `auditor.artifact` [imported-tool] `macro-technical-pulse.auditor-report.json#`: agentic-repo-auditor 0.1.0 report schema 1.2; sha256 `93505fb1c11f7675b155355a2ad9119d68ad5a793b2de7a7e10da31a937b097a`
- `auditor.configuration` [imported-tool] `macro-technical-pulse.auditor-report.json#/configuration`: {"disabled_checks":[],"evidence":{"primary_check":null,"project_contract":null}}; sha256 `93505fb1c11f7675b155355a2ad9119d68ad5a793b2de7a7e10da31a937b097a`
- `auditor.finding.agent-readiness.instructions` [imported-tool] `macro-technical-pulse.auditor-report.json#/findings/0`: {"category":"agent-readiness","description":"Repository instructions expose core evidence, verification, and safety signals.","id":"agent-readiness.instructions","remediation":"Document source precedence, tests, verification boundaries, and safety constraints.","severity":"medium","status":"warn","title":"Agent instruction coverage"}; sha256 `93505fb1c11f7675b155355a2ad9119d68ad5a793b2de7a7e10da31a937b097a`
- `auditor.finding.agent-readiness.instructions.evidence.0000` [imported-tool] `macro-technical-pulse.auditor-report.json#/findings/0/evidence/0`: {"kind":"signal-set","path":"AGENTS.md","value":"present=['source', 'test', 'verification']; missing=['safety']; matches=['source:sources', 'test:test', 'verification:verified']"}; sha256 `93505fb1c11f7675b155355a2ad9119d68ad5a793b2de7a7e10da31a937b097a`
- `auditor.finding.agent-readiness.skills` [imported-tool] `macro-technical-pulse.auditor-report.json#/findings/1`: {"category":"agent-readiness","description":"Repository skills use discoverable SKILL.md files with basic portable metadata.","id":"agent-readiness.skills","remediation":"Use one skill directory per capability with valid name and description frontmatter.","severity":"low","status":"warn","title":"Portable agent skills"}; sha256 `93505fb1c11f7675b155355a2ad9119d68ad5a793b2de7a7e10da31a937b097a`
- `auditor.finding.agent-readiness.skills.evidence.0000` [imported-tool] `macro-technical-pulse.auditor-report.json#/findings/1/evidence/0`: {"kind":"path-count","path":".agents/skills","value":"0"}; sha256 `93505fb1c11f7675b155355a2ad9119d68ad5a793b2de7a7e10da31a937b097a`
- `auditor.finding.ci.immutable-actions` [imported-tool] `macro-technical-pulse.auditor-report.json#/findings/2`: {"category":"ci","description":"External Actions and container actions use immutable references.","id":"ci.immutable-actions","remediation":"Pin third-party Actions to full commit SHAs and containers to image digests.","severity":"high","status":"fail","title":"Immutable workflow dependencies"}; sha256 `93505fb1c11f7675b155355a2ad9119d68ad5a793b2de7a7e10da31a937b097a`
- `auditor.finding.ci.immutable-actions.evidence.0000` [imported-tool] `macro-technical-pulse.auditor-report.json#/findings/2/evidence/0`: {"kind":"action-summary","path":".github/workflows","value":"references=2"}; sha256 `93505fb1c11f7675b155355a2ad9119d68ad5a793b2de7a7e10da31a937b097a`
- `auditor.finding.ci.immutable-actions.evidence.0001` [imported-tool] `macro-technical-pulse.auditor-report.json#/findings/2/evidence/1`: {"kind":"mutable-action","path":".github/workflows/ci.yml","value":"actions/checkout@v4"}; sha256 `93505fb1c11f7675b155355a2ad9119d68ad5a793b2de7a7e10da31a937b097a`
- `auditor.finding.ci.immutable-actions.evidence.0002` [imported-tool] `macro-technical-pulse.auditor-report.json#/findings/2/evidence/2`: {"kind":"mutable-action","path":".github/workflows/ci.yml","value":"actions/setup-python@v5"}; sha256 `93505fb1c11f7675b155355a2ad9119d68ad5a793b2de7a7e10da31a937b097a`
- `auditor.finding.ci.workflows` [imported-tool] `macro-technical-pulse.auditor-report.json#/findings/3`: {"category":"ci","description":"At least one repository CI workflow is present.","id":"ci.workflows","remediation":"Add CI that runs the same authoritative check used locally.","severity":"info","status":"pass","title":"Continuous integration workflows"}; sha256 `93505fb1c11f7675b155355a2ad9119d68ad5a793b2de7a7e10da31a937b097a`
- `auditor.finding.ci.workflows.evidence.0000` [imported-tool] `macro-technical-pulse.auditor-report.json#/findings/3/evidence/0`: {"kind":"path-count","path":".github/workflows","value":"1"}; sha256 `93505fb1c11f7675b155355a2ad9119d68ad5a793b2de7a7e10da31a937b097a`
- `auditor.finding.git.clean-worktree` [imported-tool] `macro-technical-pulse.auditor-report.json#/findings/4`: {"category":"git","description":"The audit records whether the target has uncommitted or untracked state.","id":"git.clean-worktree","remediation":"Review and intentionally preserve, commit, or ignore outstanding worktree entries.","severity":"info","status":"pass","title":"Worktree state"}; sha256 `93505fb1c11f7675b155355a2ad9119d68ad5a793b2de7a7e10da31a937b097a`
- `auditor.finding.git.clean-worktree.evidence.0000` [imported-tool] `macro-technical-pulse.auditor-report.json#/findings/4/evidence/0`: {"kind":"git-status","path":".","value":"changed_entries=0"}; sha256 `93505fb1c11f7675b155355a2ad9119d68ad5a793b2de7a7e10da31a937b097a`
- `auditor.finding.governance.community-files` [imported-tool] `macro-technical-pulse.auditor-report.json#/findings/5`: {"category":"governance","description":"Basic purpose, contribution, and licensing files are present.","id":"governance.community-files","remediation":"Add the missing community health files and keep them aligned with actual behavior.","severity":"low","status":"warn","title":"Community health files"}; sha256 `93505fb1c11f7675b155355a2ad9119d68ad5a793b2de7a7e10da31a937b097a`
- `auditor.finding.governance.community-files.evidence.0000` [imported-tool] `macro-technical-pulse.auditor-report.json#/findings/5/evidence/0`: {"kind":"path-set","path":".","value":"present=['README.md', 'LICENSE']; missing=['CONTRIBUTING.md']"}; sha256 `93505fb1c11f7675b155355a2ad9119d68ad5a793b2de7a7e10da31a937b097a`
- `auditor.finding.governance.instructions` [imported-tool] `macro-technical-pulse.auditor-report.json#/findings/6`: {"category":"governance","description":"Repository-level agent and contributor instructions are discoverable.","id":"governance.instructions","remediation":"Add a root AGENTS.md with commands, boundaries, sources of truth, and safety rules.","severity":"info","status":"pass","title":"Repository instructions"}; sha256 `93505fb1c11f7675b155355a2ad9119d68ad5a793b2de7a7e10da31a937b097a`
- `auditor.finding.governance.instructions.evidence.0000` [imported-tool] `macro-technical-pulse.auditor-report.json#/findings/6/evidence/0`: {"kind":"path-presence","path":".","value":"AGENTS.md"}; sha256 `93505fb1c11f7675b155355a2ad9119d68ad5a793b2de7a7e10da31a937b097a`
- `auditor.finding.governance.project-contract` [imported-tool] `macro-technical-pulse.auditor-report.json#/findings/7`: {"category":"governance","description":"No recognized project intent and authority contract or explicit disposition is present.","id":"governance.project-contract","remediation":"Add harness/project.yaml or configure a safe repository-relative contract path or explicit not-applicable reason.","severity":"medium","status":"warn","title":"Machine-readable project contract"}; sha256 `93505fb1c11f7675b155355a2ad9119d68ad5a793b2de7a7e10da31a937b097a`
- `auditor.finding.governance.project-contract.evidence.0000` [imported-tool] `macro-technical-pulse.auditor-report.json#/findings/7/evidence/0`: {"kind":"project-contract","path":"harness/project.yaml","value":"not available (absent)"}; sha256 `93505fb1c11f7675b155355a2ad9119d68ad5a793b2de7a7e10da31a937b097a`
- `auditor.finding.security.code-scanning` [imported-tool] `macro-technical-pulse.auditor-report.json#/findings/8`: {"category":"security","description":"The repository declares a CodeQL workflow as a visible code-scanning signal.","id":"security.code-scanning","remediation":"Configure code scanning appropriate to the repository languages and threat model.","severity":"medium","status":"warn","title":"Code scanning"}; sha256 `93505fb1c11f7675b155355a2ad9119d68ad5a793b2de7a7e10da31a937b097a`
- `auditor.finding.security.code-scanning.evidence.0000` [imported-tool] `macro-technical-pulse.auditor-report.json#/findings/8/evidence/0`: {"kind":"workflow-set","path":".github/workflows","value":"none found"}; sha256 `93505fb1c11f7675b155355a2ad9119d68ad5a793b2de7a7e10da31a937b097a`
- `auditor.finding.security.dependency-updates` [imported-tool] `macro-technical-pulse.auditor-report.json#/findings/9`: {"category":"security","description":"A recognized dependency-update configuration is present.","id":"security.dependency-updates","remediation":"Configure a reviewed dependency-update tool for every supported ecosystem.","severity":"medium","status":"warn","title":"Automated dependency updates"}; sha256 `93505fb1c11f7675b155355a2ad9119d68ad5a793b2de7a7e10da31a937b097a`
- `auditor.finding.security.dependency-updates.evidence.0000` [imported-tool] `macro-technical-pulse.auditor-report.json#/findings/9/evidence/0`: {"kind":"path-presence","path":".","value":"none found"}; sha256 `93505fb1c11f7675b155355a2ad9119d68ad5a793b2de7a7e10da31a937b097a`
- `auditor.finding.security.policy` [imported-tool] `macro-technical-pulse.auditor-report.json#/findings/10`: {"category":"security","description":"A vulnerability-reporting policy is discoverable.","id":"security.policy","remediation":"Add SECURITY.md with supported versions and a private reporting channel.","severity":"medium","status":"warn","title":"Security policy"}; sha256 `93505fb1c11f7675b155355a2ad9119d68ad5a793b2de7a7e10da31a937b097a`
- `auditor.finding.security.policy.evidence.0000` [imported-tool] `macro-technical-pulse.auditor-report.json#/findings/10/evidence/0`: {"kind":"path-presence","path":".","value":"none found"}; sha256 `93505fb1c11f7675b155355a2ad9119d68ad5a793b2de7a7e10da31a937b097a`
- `auditor.finding.testing.primary-check` [imported-tool] `macro-technical-pulse.auditor-report.json#/findings/11`: {"category":"testing","description":"A machine-readable primary verification command is declared.","id":"testing.primary-check","remediation":"Declare one authoritative command and run it unchanged in local and CI boundaries.","severity":"medium","status":"warn","title":"Authoritative local and CI check"}; sha256 `93505fb1c11f7675b155355a2ad9119d68ad5a793b2de7a7e10da31a937b097a`
- `auditor.finding.testing.primary-check.evidence.0000` [imported-tool] `macro-technical-pulse.auditor-report.json#/findings/11/evidence/0`: {"kind":"primary-check","path":"harness/project.yaml","value":"not available (absent)"}; sha256 `93505fb1c11f7675b155355a2ad9119d68ad5a793b2de7a7e10da31a937b097a`
- `auditor.finding.testing.suite` [imported-tool] `macro-technical-pulse.auditor-report.json#/findings/12`: {"category":"testing","description":"A conventional automated test suite is present.","id":"testing.suite","remediation":"Add deterministic tests for the project's public and failure-path behavior.","severity":"info","status":"pass","title":"Automated tests"}; sha256 `93505fb1c11f7675b155355a2ad9119d68ad5a793b2de7a7e10da31a937b097a`
- `auditor.finding.testing.suite.evidence.0000` [imported-tool] `macro-technical-pulse.auditor-report.json#/findings/12/evidence/0`: {"kind":"path-count","path":"tests","value":"4"}; sha256 `93505fb1c11f7675b155355a2ad9119d68ad5a793b2de7a7e10da31a937b097a`
- `auditor.summary` [imported-tool] `macro-technical-pulse.auditor-report.json#/summary`: {"by_severity":{"high":1,"info":4,"low":2,"medium":6},"by_status":{"fail":1,"not-applicable":0,"pass":4,"unknown":0,"warn":8},"total":13}; sha256 `93505fb1c11f7675b155355a2ad9119d68ad5a793b2de7a7e10da31a937b097a`
- `context.application.purpose` [human-declared] `macro-technical-pulse.context.json#/application/purpose`: Capture and gather economic and market data streams, store them for feature engineering and machine-learning price-prediction models, deploy trained models on live streams, and provide visualization of the collected data, engineered features, signals, and predictions. Technical-response measurement may later analyze price sensitivity to external signals, but it is not the application's primary purpose.
- `context.application.stakeholders` [human-declared] `macro-technical-pulse.context.json#/application/stakeholders`: Jack Rory Staunton; application maintainers; economic and market data researchers; feature-engineering and model developers; model validators; independent risk reviewers
- `context.review` [human-declared] `macro-technical-pulse.context.json#/review`: accepted on 2026-08-25 from questionnaire answers from owner interview: Jack Rory Staunton
- `static.documentation.07cafbb1f0ce74f3` [observed] `docs/migration-map.md`: recognized regular file; sha256 `8f7bee85d90348b984485af4225fa05900bb7eed1bb1a0a1868aae397c831cde`
- `static.documentation.1224e6e12751eccd` [observed] `docs/decisions/0003-modular-monolith-and-artifacts.md`: recognized regular file; sha256 `bc12ae0f7f9d98c3943a7727a69e294d9b4ebb3ae99b86f95d50bfcd68f1d2b6`
- `static.documentation.140eef3ba41bdcf4` [observed] `docs/architecture.md`: recognized regular file; sha256 `33460a8388d8da4c508a7677a89f3a8dbe7bf4fe1d4aa6494cf43c84532aca35`
- `static.documentation.2691a08d3224e00b` [observed] `docs/risk/0001-us-gold-venue-paper-readiness-review.md`: recognized regular file; sha256 `388acf4c4d2398282ff363bb55879abee92f14e8e7da103a4f7fe48394778d86`
- `static.documentation.331194f29b41b3cf` [observed] `docs/decisions/0001-research-only-scope.md`: recognized regular file; sha256 `29d4bd1cebf827f4b1c4ccc66d3fdf01cb70453355093bccb04728a0fb320cbe`
- `static.documentation.34ca10206a556cc5` [observed] `docs/decisions/0004-point-in-time-evaluation.md`: recognized regular file; sha256 `0a5a6b2508cfbae659a8a264609620b14b5a9e2f216d22c59002119626a1778f`
- `static.documentation.4a568930dc44e58e` [observed] `docs/legacy-review.md`: recognized regular file; sha256 `f71c6087d5fe1cde1da93c2d0d08d16e71c4264d3fd54ee5d2145631b2fe84cf`
- `static.documentation.4d455a3fae963eb9` [observed] `docs/research/0003-us-gold-venue-instrument-and-action-time.md`: recognized regular file; sha256 `630294c0d5bc31feedaf071f817f9350ecf2255dfad55a98784f65abca558445`
- `static.documentation.572ae509bffb4c08` [observed] `docs/risk/0002-gold-gate-a-offline-readiness-review.md`: recognized regular file; sha256 `47f61ef4f2df53ee963be61ef70a641584bf504b29d92eb580e25656ba853f8d`
- `static.documentation.5bb6ca8b3d3e312a` [observed] `docs/decisions/0005-provider-ports-and-secrets.md`: recognized regular file; sha256 `6f0a1604d13b4d802cd8c532f1fc7c953ad5e26182ad43bfb3ce1760fe23b2da`
- `static.documentation.6a17656d764b8e19` [observed] `docs/roadmap.md`: recognized regular file; sha256 `b3c6501b3d41cf5b9fe39ef532cef3125205071704ee9c82bd649e15371a34f0`
- `static.documentation.7530a4938bbb6358` [observed] `docs/vision.md`: recognized regular file; sha256 `c9f2ce9d76e4ffcce30d6507267b889ced079408d1c59e904f2a633e36e045af`
- `static.documentation.88af4fc154e5dd1a` [observed] `docs/development/github-plan.md`: recognized regular file; sha256 `8acbfe4433db4e60447507ac0f2529ca5f27640ad89565c837834a910cf13ca1`
- `static.documentation.88ddaaf9fac7e945` [observed] `docs/decisions/0009-parallel-capability-projects.md`: recognized regular file; sha256 `59ce3d95bd0394ea78d23713bb7b68b879eb12f7af79b5efd19201f729e7e504`
- `static.documentation.8f260c38c840d041` [observed] `docs/research/0002-free-open-data-and-technical-analysis-tools.md`: recognized regular file; sha256 `2d641767767cbd3d107b9a464f757648b65e3e78e56a441ff295ca605d7892da`
- `static.documentation.9b12de6ee2f2dcd5` [observed] `docs/decisions/0002-separate-agent-roles.md`: recognized regular file; sha256 `00f21c8a264aa4b63e8d424bc29645d8db5ea78d60cdb7a1488cfc9919950b4f`
- `static.documentation.a54ff182c7e8acf5` [observed] `AGENTS.md`: recognized regular file; sha256 `907e1d328effbd95652a1a360cefe3a2a0e85a7a9e12389e9a7bd4694f3a75f3`
- `static.documentation.a96dded28a6ad5a2` [observed] `docs/roles.md`: recognized regular file; sha256 `f18d943d1ebf25cac4be1495230655ffb8abcc3dbb11975dab504c6103e473ef`
- `static.documentation.ad0c3c11e948e3b4` [observed] `docs/decisions/0006-reimplement-from-evidence.md`: recognized regular file; sha256 `6baa3cee0c9271d55a09cb0cdeceec3ba722cac4c0298e723d89f021896850eb`
- `static.documentation.b335630551682c19` [observed] `README.md`: recognized regular file; sha256 `4d8d6a8fe01018db67a20dc0bc750d8dff74c20506c6ac6beff07692220629c1`
- `static.documentation.bd5046628cb32b48` [observed] `docs/development/milestone-map.md`: recognized regular file; sha256 `65c42adc7852f9b5802ae9c0ed2fefb23decb549cff6e11ea106b3d92eaa744c`
- `static.documentation.c0269be49df6f070` [observed] `docs/open-questions.md`: recognized regular file; sha256 `acb37c2b28b727fd9232b9fff0e2054622b051794034add3092df5cc34da6961`
- `static.documentation.c8a0cf590733b81c` [observed] `docs/decisions/0010-mit-source-license.md`: recognized regular file; sha256 `0fa15ecabfe0555dc5a77ba4e903205481bfa2f68678da0c04c08a443cb2d574`
- `static.documentation.c90069cb1bc1be4f` [observed] `docs/decisions/0007-event-time-pulse-model.md`: recognized regular file; sha256 `e4a2069117d7d051ac07340e5aa45c8a925659670ab0749a65625e439e1ce35e`
- `static.documentation.ca9bc16ff98cd2f1` [observed] `docs/research/0004-gold-gate-a-offline-fixture.md`: recognized regular file; sha256 `88dede29200f82d012dbfa7e68b24d501718638f4f704ae5790b80d2ddfeb7bb`
- `static.documentation.d4829006cb0f9e10` [observed] `docs/decisions/0008-us-exchange-traded-gold-paper-target.md`: recognized regular file; sha256 `ee8a7ec6bd152824eb4424d5940ba3cdaad179e05ef3bc061b85d6d98359b67d`
- `static.documentation.dff5573bf0c37ecf` [observed] `docs/research/0001-macro-signal-frequency-and-market-irf.md`: recognized regular file; sha256 `317587743fb5e1226b83aee19e417e81125a44d7757b952d2ad8b6ceaad176f5`
- `static.entrypoint.5a6aebcf596216e8` [observed] `src/macro_technical_pulse/__main__.py`: recognized regular file; sha256 `935a1c1166b0c1ea35a82256345000bf2c73ded718d77773bc27a71ecce28f7d`
- `static.entrypoint.d071d0baada3bc88` [observed] `src/macro_technical_pulse/cli.py`: recognized regular file; sha256 `54f44c8579981748c94e61fd019c8777b0c84b53e53330a4e60818f826405710`
- `static.manifest.50c86b7ed8ac2cf9` [observed] `pyproject.toml`: recognized regular file; sha256 `d8d37364dcb864a7350ad05ac78e5d2ca754a085239e7514653324b863f555da`
- `static.test.24e2d1e2ad448ca2` [observed] `tests/test_workflow.py`: recognized regular file; sha256 `a280a97a55bfdfc4f68da3ff44986c247708d6ffd9c41bfd096a9154db5e671c`
- `static.test.28081c8b057714df` [observed] `tests/test_gold_gate_a.py`: recognized regular file; sha256 `b1b708875a2f03f294c6ee4414823eb34a271ebee26874750569f3424a41bb34`
- `static.test.3d90225e015d0cca` [observed] `tests/test_gold_execution.py`: recognized regular file; sha256 `83fb19369b04ebfe2f89fcb2156c3e2b69f84d7f9e2d68535435c1cd53158eda`
- `static.test.bb1dbe1e91dfbf28` [observed] `tests/test_contracts.py`: recognized regular file; sha256 `d94fc8da36365b8530c2d2d259aa2b78372f1d76bc390d9c03c47e1fc5d931b6`

This report does not claim runtime coverage, security approval, compliance, release readiness, or intended architecture beyond accepted declarations.
