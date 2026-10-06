"""Campagnes bornées sur les deux parseurs exposés : nombres CLI et TOML."""

import contextlib
import io
import tempfile
from pathlib import Path

from hypothesis import given, settings
from hypothesis import strategies as st

from portage.cli import main


@settings(max_examples=150, deadline=1000)
@given(st.text(max_size=80))
def test_generated_numeric_cli_input(text: str) -> None:
    with contextlib.redirect_stdout(io.StringIO()), contextlib.redirect_stderr(io.StringIO()):
        try:
            status = main(["simuler", "--tjm=" + text, "--json"])
            assert status in (0, 2)
        except SystemExit as exc:
            assert exc.code == 2


@settings(max_examples=150, deadline=1000)
@given(st.binary(max_size=1024))
def test_generated_toml_and_unicode(raw: bytes) -> None:
    with tempfile.TemporaryDirectory(prefix="portage-fuzz-") as directory:
        path = Path(directory) / "profile.toml"
        path.write_bytes(raw)
        with contextlib.redirect_stdout(io.StringIO()), contextlib.redirect_stderr(io.StringIO()):
            assert main(["simuler", "--profil", str(path), "--json"]) in (0, 2)


def test_structured_wrong_types_and_duplicates() -> None:
    bodies = [
        '[simulation]\nfrais = ["12"]',
        '[simulation]\nfrais = {a = "12"}',
        '[simulation]\nfrais = "1"\nfrais = "2"',
        "[simulation]\n[simulation]",
        "[simulation]\nfrais = 2026-01-01",
        "[simulation]\nfrais = inf",
        "[simulation]\nfrais = nan",
        '[simulation]\nmois = "2026-10\\u001b"',
    ]
    with tempfile.TemporaryDirectory(prefix="portage-fuzz-") as directory:
        path = Path(directory) / "profile.toml"
        for text in bodies:
            path.write_text(text)
            with (
                contextlib.redirect_stdout(io.StringIO()),
                contextlib.redirect_stderr(io.StringIO()),
            ):
                assert main(["simuler", "--profil", str(path)]) == 2
