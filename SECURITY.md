# Security and calculation scope

## Trust boundaries

- User input: CLI arguments and a local TOML profile. Values are finite, bounded, validated.
- Optional atelier: local curses screen and bounded 32-character keyboard editing; no browser,
  server, mouse capture, shared session or persistence. It reuses the same Decimal engine.
  Indicators depend on user declarations and contract parameters, never an Urssaf audit score.
- Output: terminal/JSON, deliberately contains the user's supplied financial assumptions.
- Runtime: Python standard library only; no network, subprocess, remote URL, authentication,
  database, automatic persistence, upload or transaction. `profil` alone creates a file,
  exclusively (never overwrites existing files or symlinks).
- Supply chain: Python, uv, locked development/build packages, pinned CI actions and scanner.
  GitHub Actions uses disposable hosted runners, read-only token, no production secrets.
- Data: public examples are synthetic. Private profiles belong outside the repository or in
  ignored `private/` / `*.local.toml` files. Gitignore is a convenience, not an access control.

## Invariants

Invalid inputs fail with exit 2; mismatch in reconciliation exits 1. A target outside the
configured budget/caps is refused. No deficit is silently funded. Residual cents are shown.
No arbitrary code from a profile executes. No existing file is changed by profile creation.
A passing reconciliation is arithmetic agreement, not proof of regulatory compliance.

## Reporting and response

Owner: Olivier Dehareng. Report a vulnerability through GitHub private vulnerability reporting
on this repository's Security tab. Do not post profiles, payslips or credentials in public
issues. For numerical bugs, provide a minimal synthetic reproducer and the expected equation.

Triage: reproduce locally with synthetic data, preserve version/input without personal data,
add a regression, correct via reviewed PR and publish an advisory/changelog if results changed.
If a release is materially wrong, mark it affected, stop recommending it and recommend a known
unaffected tag (or suspend use if none exists). Roll back by reinstalling the previous tag;
profiles are untouched. No hosted service, user accounts, application tokens or database to
revoke/restore. If a repository credential leaks, revoke it at GitHub immediately, rotate it,
scan all history; deleting a commit does not revoke a credential.

Supported version: latest 0.1.x. Review sources and dependencies at each release; Dependabot
checks weekly. No hosted availability/on-call promise. See docs/READINESS.md for actual evidence
and any unresolved release controls. An agent review is not a human penetration test.
