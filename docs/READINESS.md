# Readiness register — simulateur-salaire-portage-france

Canonical standards: CODING-RULES.md / SECURITY-CHECKLIST.md **2026-10-05.1**.
Reviewed 2026-10-06. Owner for every row: Olivier Dehareng. Recheck at each release or
change to the relevant surface. This is evidence scoped to a local CLI, not a payroll certification.

## 1. Profile and applicability

| Component | Level | Scope |
|---|---|---|
| CLI, Decimal engine, TOML profiles | L2 | Nonbinding local calculation, no authority to run payroll or move funds |
| GitHub source and CI | L2 | Public source, hosted ephemeral checks, no deployment service |

Data: synthetic examples only in the repository. Financial inputs remain in the user's local
process/files; no third-party sensitive records, retained sessions, server, database, telemetry,
network access, account system, emails, transactions or external API at runtime. `profil`
exclusively creates an explicitly selected file. Dev tooling talks to PyPI/GitHub; runtime does not.

L2 rationale: bounded recoverable informational use, no accounting system of record or financial
execution. Using this code as authoritative payroll would require a new L3 assessment, statutory
engine validation, human acceptance and the applicable human pentest. It is not currently supported.

## 2. Engineering baseline

| Control | Status | Evidence |
|---|---|---|
| Formatter / lint / strict types | PASS | Ruff, Ruff S rules, mypy strict, local clean run 2026-10-06 |
| Critical arithmetic | PASS | Hand-calculated fixture, budget conservation properties, all PAS thresholds, brute-force target oracle |
| Coverage | PASS | Local coverage ≥99%; model/money 100%; CI global floor 90%, critical floor 100%, PR changed-code floor 90% |
| Import architecture | PASS | AST-enforced layer graph in test_architecture.py, no cycles or runtime network/process modules |
| Integration / E2E | PASS | TOML roundtrip/override, real CLI subprocess, wheel install smoke test |
| Boundary fuzzing | PASS | 150 generated CLI values + 150 binary TOML inputs, wrong types/duplicates/oversized/deep nesting |
| Mutation testing | PASS | Five isolated mutants killed: commission cap, employee meals sign, target comparison, rounding, PAS threshold |
| Independent review | PASS | docs/REVIEW.md; two findings fixed with red/green regressions |
| Reproducibility | PASS | .python-version, uv.lock, frozen installs, pinned build backend and CI action SHAs |
| Platform branch protection | PASS | GitHub protection GET 2026-10-06: strict quality + independent-review checks, PR required, CODEOWNERS for sensitive paths, enforce_admins=true, no force/deletion, conversation resolution |
| Hosted CI executed | PASS | [Run 37452500060](https://github.com/DeharengOlivier/simulateur-salaire-portage-france/actions/runs/37452500060), all applicable steps successful on 05a99b9; final head must also pass checks |
| Build / install / reinstall | PASS | uv build --no-build-isolation; isolated /tmp venv installed and reinstalled wheel, version and bulletin smoke passed; two builds with fixed SOURCE_DATE_EPOCH yielded identical hashes |
| Services / UI / DB / queues / load / alerts / backups | NOT_APPLICABLE | No hosted service, browser UI, persistence or automated high-impact operation; user profiles are unmanaged local files |

## 3. Security control evidence

Applicability is explicit. PASS means the evidence below, not a universal assertion of safety.
P1 deferred items are discussed in section 4. No applicable P0 may remain FAIL/NOT_VERIFIED at release.

| Control | Priority | Status | Evidence / rationale |
|---|---|---|---|
| SEC-GOV-01 | P0 | PASS | This scoped register, canonical version and release gate recorded |
| SEC-GOV-02 | P0 | PASS | Local synthetic tests in temporary directories; network guard; no production effects |
| SEC-01-001 through SEC-01-007 | P0 | PASS | SECURITY.md inventories inputs, data, actors, supply chain, absence of app secrets, and file-creation effect |
| SEC-07-001, SEC-07-003, SEC-07-004 | P0 | PASS | Central Decimal/Scenario validation, TOML allowlist, size and numeric bounds, unknown keys refused |
| SEC-07-002 | P0 | NOT_APPLICABLE | No server/frontend split; same local boundary validates all input |
| SEC-07-005 | P0 | PASS | test_fuzz.py plus test_deeply_nested_toml_is_safe_error, invalid profiles and numeric edge cases |
| SEC-08-003, SEC-08-006 | P0 | PASS | Runtime has no shell, subprocess, eval or dynamic code; AST layer checks, TOML only |
| SEC-12-001, SEC-12-002, SEC-12-004, SEC-12-008 | P0 | PASS | Gitleaks full history redacted local scan and successful hosted CI Scan full history for secrets; no leaks |
| SEC-12-010 | P0 | PASS | Parser errors do not echo TOML payload or traceback; sentinel test and nesting regression |
| SEC-13-001, SEC-13-003, SEC-13-004, SEC-13-006, SEC-13-007 | P0 | PASS | Locked PyPI test/build tools only; no runtime dependencies; each added tool has a check/build purpose |
| SEC-13-002 | P0 | PASS | Final uv.lock export audited locally and in run 37452500060 including build/dev dependencies; no known vulnerabilities |
| SEC-13-005 | P0 | PASS | Dependabot weekly uv + GitHub Actions updates; source review at each release |
| SEC-13-008, SEC-13-009 | P0 | PASS | CI permissions contents:read; checkout without persisted credentials; actions pinned to verified SHAs; Gitleaks archive SHA256 pinned |
| SEC-14-001, SEC-14-002 | P0 | PASS | GitHub API confirms PR/check enforcement and no admin bypass. independent-review is a required status issued only after recorded agent review; CODEOWNERS additionally requires owner approval for sensitive paths |
| SEC-14-003, SEC-14-004 | P0 | PASS | GitHub API 2026-10-06: owner MFA enabled; sole collaborator is owner |
| SEC-14-005 | P0 | PASS | GitHub vulnerability-alerts HEAD succeeds; required quality check includes full-history Gitleaks and locked dependency audit; Dependabot configured |
| SEC-14-006 | P0 | PASS | GitHub commit/check history; no financial transaction audit trail needed |
| SEC-14-007, SEC-14-008, SEC-14-013 | P0 | PASS | Hosted ubuntu runner, read-only token, no production credentials, no pull_request_target |
| SEC-14-009 through SEC-14-012 | P0 | NOT_APPLICABLE | No deployed production service or promotion pipeline; publication is versioned source/wheel |
| SEC-17-010, SEC-17-011, SEC-17-013, SEC-17-016 | P0/P1 | PASS | No personal data in published fixtures, no automatic runtime logs; explicit financial stdout only |
| SEC-18-004, SEC-19-005 | P0 | PASS | No paid operations or remote runtime I/O; bounded CLI data/search; CI timeout 10 min, curl timeout 60 s |
| SEC-19-002 | P0 | PASS | Controlled errors and exit codes; malformed/deep TOML produces typed rejection |
| SEC-19-004, SEC-19-006, SEC-22-RACES | P0 | NOT_APPLICABLE | No transactions/replayed writes; sole file creation uses exclusive open, tested against existing files/symlinks |
| SEC-20-005, SEC-20-006, SEC-20-013, SEC-20-014, SEC-20-015 | P0/P1 | PASS | SECURITY.md owner/runbook; isolated wheel install/reinstall leaves profiles untouched. First release has no prior supported version; withdraw/suspend if no unaffected version exists |
| SEC-22-INVARIANTS, SEC-22-REGRESSION | P0 | PASS | Safe profile handling and arithmetic constraints tested; independent findings reproduced red then fixed green |
| SEC-22-MUTATION | P1 | PASS | Five isolated mutants killed on 2026-10-06 (see REVIEW.md) |
| SEC-22-EXPLORE | P1 | PASS | CLI commands, invalid configuration, unattainable target, actual wheel and independent agent review |
| SEC-22-PENTEST | P1 | NOT_VERIFIED | No human pentest; informational local L2 scope, no exposed auth/infrastructure surface |

The following controls are **NOT_APPLICABLE**, because the corresponding surface is absent:
sections 4–6 authentication/authorization/sessions; section 8 SQL/HTML controls except rows above;
section 9 HTTP/API/SSRF/webhooks; sections 10–11 server-side workflow/upload controls;
section 12 application secret storage/rotation/images/frontend (no app secrets/images/frontend);
SEC-13-010 containers; section 15 infrastructure; section 16 browser; section 17 DB/replication/
processor controls and persistent sensitive-data retention; section 18 authentication alerts/
service quotas; section 20 account disablement, server isolation and persistent-data backups;
SEC-22-MODEL/FUZZ/DAST/LLM when conditional on stateful authorization, public API, exposed
application or LLM (none exists). General parser fuzzing still applies and is tested above.

## 4. Accepted constraints / P1 decisions

Owner: Olivier Dehareng; review each release. No human pentest claimed; reconsider if a server,
identity, real payroll storage or transaction is introduced. No human payroll validation claimed;
`simulation` output is explicitly provisional. Statutory contribution engine / annual cumulative
regularization is outside current functionality, not silently approximated as exact. Effective
rates and all limits are user-supplied; defaults are illustrative. Sources are dated in README.
No production monitoring, data backups, alerts or 24/7 operator are invented for a local calculator.

## 5. Release log

| Date | Version | Gate | Open blockers |
|---|---|---|---|
| 2026-10-06 | 0.1.0 preparation | PASS for checked scope | No outstanding applicable P0; publication still conditional on green final-head checks and independent review |

## Repository bootstrap and review enforcement

The initial source was imported while the new repository was private, independently reviewed,
and passed hosted checks. Main protection was installed before public publication. Subsequent
changes, including this evidence update, go through PR. The required `independent-review` status
is recorded on the exact reviewed commit after the agent verdict; GitHub approval count is zero
for nonsensitive files because L2 permits recorded agent review. CODEOWNERS approval is required
for CI, security policy, dependency manifests and calculation/input-boundary modules. The
maintainer must not manufacture a successful review status without an actual independent review.
This does not claim two-person human approval of the initial code or a human pentest.

## Atelier terminal — 2026-10-06 (change pending release)

Scope stays L2: optional local curses UI, macOS/Linux and WSL, no HTTP/browser or network.
The terminal is an additional input/output surface, not a web session. No new dependencies,
credentials or persisted records. Existing server/browser N/A decisions remain applicable.
Owner Olivier Dehareng; reassess on release and input/calculation changes.

| Control | Priority | Status | Evidence |
|---|---|---|---|
| SEC-GOV-01, SEC-01-001..007 | P0 | PASS | AGENTS/SECURITY updated for bounded terminal input and transient output |
| SEC-07-001..005, SEC-22-INVARIANTS | P0 | PASS | Workshop validates via Decimal/Scenario; immutable refused edits; input fuzz; entry limited to 32 characters |
| SEC-08-003, SEC-08-006, SEC-12-010 | P0 | PASS | No shell or eval; architecture test; safe ValueError display; imports constrained |
| SEC-17-010, SEC-17-013, SEC-17-016 | P0/P1 | PASS | Synthetic tests only; financial screen is explicitly requested; no recording or logs |
| SEC-19-002 | P0 | PASS | Impossible budget, target, invalid input, missing curses/non-TTY and resize paths tested; wrapper restores terminal |
| SEC-22-EXPLORE | P1 | PASS | Real macOS PTY journey: edit TJM, switch control, solve, inspect help, quit; automated PTY journey retained |
| Critical arithmetic / UI journey | required L2 | PASS | Same engine, inverse minimality regression, all three added modules 100% branch coverage; 79 tests locally |
| Supported layouts | required L2 | PASS | 80×24 / 120×40 rendering and small-terminal refusal; help scrolls, keyboard-only interaction |
| Independent review / final CI / required owner approval | required L2 | NOT_VERIFIED | Pending reviewed PR; new sensitive paths added to CODEOWNERS |

Release remains BLOCKED until final-head CI, independent review and required CODEOWNERS
approval are confirmed. This records the publication gate, not an observed exploit. No human
pentest or legal validation is claimed. Stopping the atelier clears the transient display and
restores the terminal; returning to v0.1.0 removes the feature without changing user profiles.

Targeted mutation checks: three isolated mutants killed (justification boundary, inverse-result
centime, fine-adjustment increment). Independent review identified two display defects;
regressions now cover lossless rate display and explicit multi-alert overflow at 80×24.
