# Independent review — 2026-10-06

Agent review, not human acceptance, pentest or payroll certification. Scope: new local CLI,
Decimal model, target search, TOML boundary, public docs and tests. Requested without parent
conversation history through the requesting-code-review workflow.

## Findings and remediation

1. P2: target solver could search above the accepted €1m expense domain after a positive budget
   adjustment. Regression `test_objective_large_budget_respects_input_domain` failed before the
   fix; upper bound now uses min(available budget, monetary limit). It passes after the fix.
2. P2: deeply nested (~3 KB) TOML caused uncaught RecursionError despite the size cap.
   `test_deeply_nested_toml_is_safe_error` failed before the fix; controlled parse rejection now
   handles it. Generated parser cases added, including bytes, wrong types, duplicates and Unicode.

Review found no ordinary-range arithmetic defect or private financial data in inspected source.
L2 informational scope judged defensible; not a replacement for authoritative payroll software.
Reviewer explicitly did not attest statutory correctness, dependency status, actual GitHub
configuration, CI execution or whole release readiness. Those are tracked in READINESS.md.

## Additional numerical evidence

Five mutations were applied one at a time to isolated temporary source/test copies (not to
production or this working tree), each with a 30-second timeout. All five were killed by tests:

| Mutation | Result |
|---|---|
| Ignore commission cap | 1 failing test |
| Add instead of subtract employee meal contribution | 1 failing test |
| Target comparator >= changed to > | 2 failing tests |
| HALF_UP changed to HALF_EVEN | 1 failing test |
| PAS upper-exclusive threshold changed to inclusive | 1 failing test |

All normal tests then pass. Monetary boundary, independent hand calculation and brute-force
small-budget oracle tests substantiate the target algorithm; tests do not establish completeness
of French payroll rules.

## Final review follow-up

Both runtime fixes were independently verified; 65 tests passed in the reviewer's run.
The reviewer approved runtime changes and identified one release-build issue: isolated
`uv build` did not honor transitive build dependencies from uv.lock. Changed both CI and
the documented command to `uv build --no-build-isolation`, after frozen installation
of the locked build backend and dependencies. Remote controls remain separately verified.

Build correction verified locally and in hosted run 37452500060. All 65 tests pass;
overall coverage 99.50%, model and money modules 100%. Gitleaks and dependency audit pass.
GitHub protection was read back before public publication; details are in READINESS.md.

## Atelier terminal, 2026-10-06

Independent agent `review_portage` reviewed the delta from a1403a2. It independently ran
77 tests and found two P2 defects: six-decimal rates displayed with two decimals, and hidden
red alerts at 80×24. Both were reproduced and corrected with explicit regressions. The
subsequent suite has 79 tests; arithmetic still uses the original engine. Re-review and final
CI are pending; no owner approval or human pentest is claimed.
