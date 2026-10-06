# Project instructions

Local CLI, Python stdlib only at runtime. French user interface. Financial **estimates**, no
payment or payroll submission, no network, no persisted personal data. L2 informational tool.
Never claim payroll accuracy from Decimal alone. `bulletin` recomposes known monetary totals;
`simuler` and `objectif` use explicitly adjustable effective rates and carry an estimate notice.

Read `docs/READINESS.md` before release or control changes. If this checkout is inside Olivier's
workspace, read canonical CODING-RULES.md and SECURITY-CHECKLIST.md at the workspace root,
section 0 and relevant controls. Do not invent absence of applicable controls as PASS.

- Money: Decimal, half-up cents, no floats, explicit units and aggregation assumptions.
- No real payslips, names of customers, addresses, bank data or personal financial examples.
- No config execution: TOML schema, bounded values, exclusive creation and no hidden writes.
- Dependency direction: money <- tax <- model <- cli. `__main__` imports cli only.
- Check: `uv sync --frozen`, `uv run ruff check .`, `uv run ruff format --check .`,
  `uv run mypy`, `uv run pytest`, dependency audit documented in README, `uv build`.
- Changes through PR, protected main, independent review. Bootstrap import is reviewed before
  the first push; main protection is installed before public release.
- Do not introduce external services or application secrets.
