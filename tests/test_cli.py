import json
import subprocess
import sys
from pathlib import Path

import pytest

from portage.cli import example_profile, main, profile


def test_profile_roundtrip_and_override(tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    path = tmp_path / "profile.toml"
    assert main(["profil", str(path)]) == 0
    assert profile(path)["jours"] == 20
    capsys.readouterr()
    assert main(["simuler", "--profil", str(path), "--jours", "22", "--json"]) == 0
    data = json.loads(capsys.readouterr().out)
    assert data["hypotheses"]["jours"] == "22"
    assert data["mode"] == "simulation"
    original = path.read_text()
    assert main(["profil", str(path)]) == 2
    assert path.read_text() == original
    assert "existant" in capsys.readouterr().err


def test_profile_cannot_overwrite_symlink(tmp_path: Path) -> None:
    target = tmp_path / "precious"
    target.write_text("unchanged")
    link = tmp_path / "profile.toml"
    link.symlink_to(target)
    assert main(["profil", str(link)]) == 2
    assert target.read_text() == "unchanged"


@pytest.mark.parametrize(
    "content",
    [
        "[unexpected]\nx=1",
        '[simulation]\nsecret="never-echo-this"',
        "[simulation]\ngestion=5.5",
        "[simulation]\nmois=2026",
        "[simulation]\ntjm=true",
        '[simulation]\nx="unterminated',
        "#" * 65537,
        "simulation = 1",
    ],
)
def test_invalid_profiles(content: str, tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    path = tmp_path / "profile.toml"
    path.write_text(content)
    assert main(["simuler", "--profil", str(path)]) == 2
    output = capsys.readouterr()
    assert "never-echo-this" not in output.err
    assert not output.out
    assert "Traceback" not in output.err


def test_missing_and_non_utf8_profile(tmp_path: Path) -> None:
    path = tmp_path / "profile.toml"
    assert main(["simuler", "--profil", str(path)]) == 2
    path.write_bytes(b"\xff")
    assert main(["simuler", "--profil", str(path)]) == 2


def test_target_and_human_output(capsys: pytest.CaptureFixture[str]) -> None:
    assert main(["objectif", "--net", "4000", "--plafond-gestion", "aucun"]) == 0
    out = capsys.readouterr().out
    assert "net versé" in out
    assert "Hypothèses" in out
    assert "paie future non garantie" in out
    assert main(["objectif", "--net", "999999", "--plafond-frais", "0"]) == 2
    assert "inaccessible" in capsys.readouterr().err


def test_bulletin_match_and_mismatch(capsys: pytest.CaptureFixture[str]) -> None:
    args = [
        "bulletin",
        "--brut",
        "3000",
        "--cotisations",
        "630",
        "--csg-non-deductible",
        "85,50",
        "--pas",
        "130",
        "--json",
    ]
    assert main(args + ["--net-attendu", "2240"]) == 0
    result = json.loads(capsys.readouterr().out)
    assert result["resultat"]["ecart_net"] == "0.00"
    assert result["mode"] == "reconstitution"
    assert main(args + ["--net-attendu", "2240,01"]) == 1
    assert json.loads(capsys.readouterr().out)["resultat"]["ecart_net"] == "-0.01"
    assert main(args[:-1]) == 0
    assert "BULLETIN" in capsys.readouterr().out


@pytest.mark.parametrize("args", [["simuler", "--jours", "NaN"], ["simuler", "--wat"], []])
def test_parser_errors(args: list[str]) -> None:
    with pytest.raises(SystemExit) as exc:
        main(args)
    assert exc.value.code == 2


def test_profile_template_is_deterministic() -> None:
    assert example_profile().startswith("# Taux effectifs")


def test_entrypoint_e2e(tmp_path: Path) -> None:
    # Actual process, isolated cwd; installed package, no network needed.
    run = subprocess.run(
        [sys.executable, "-m", "portage", "simuler", "--tjm", "450", "--jours", "20", "--json"],
        cwd=tmp_path,
        text=True,
        capture_output=True,
        check=True,
        timeout=10,
    )
    assert json.loads(run.stdout)["resultat"]["chiffre_affaires"] == "9000.00"
    assert not run.stderr


def test_deeply_nested_toml_is_safe_error(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    path = tmp_path / "nested.toml"
    path.write_text("[simulation]\nfrais = " + "[" * 1500 + "0" + "]" * 1500)
    assert main(["simuler", "--profil", str(path)]) == 2
    assert "Traceback" not in capsys.readouterr().err
