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
