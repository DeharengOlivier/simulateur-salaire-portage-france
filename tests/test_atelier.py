"""Parcours de l'atelier et limites financières, sans terminal ni réseau requis."""

import curses
from dataclasses import replace
from decimal import Decimal as D
from typing import Any

import pytest
from hypothesis import given
from hypothesis import strategies as st

from portage.advisory import assess
from portage.atelier import CONTROLS, Workshop
from portage.cli import main
from portage.model import Scenario, simulate, target_expenses
from portage.terminal import display, draw, interact, launch, read_value, write


def test_workshop_same_engine_and_minimum() -> None:
    s = Scenario(tjm=D("400"), jours=D("22"), taux_pas=D("5"))
    state = Workshop(s, D("4500"))
    expected = target_expenses(s, D("4500"))
    state.solve()
    assert state.scenario.frais == expected["frais"]
    assert state.snapshot()[0] == simulate(state.scenario)
    assert (
        simulate(replace(state.scenario, frais=state.scenario.frais - D(".01")))["net_verse"]
        < state.target
    )
    assert any(a.level == "VIGILANCE" for a in state.snapshot()[1])


def test_refused_edit_and_target_do_not_mutate() -> None:
    state = Workshop(Scenario(), D("1000000"))
    with pytest.raises(ValueError, match="inaccessible"):
        state.solve()
    assert state.scenario == Scenario()
    with pytest.raises(ValueError):
        state.set_value("-1")
    state.selected = 1
    with pytest.raises(ValueError):
        state.set_value("1.25")
    assert state.scenario == Scenario()


def test_optional_signed_and_exact_adjustments() -> None:
    state = Workshop(Scenario())
    state.adjust(1)
    state.adjust(-1, fine=True)
    assert state.scenario.tjm == D("504.99")
    state.move(-1)
    assert state.selected == len(CONTROLS) - 1
    state.move(1)
    assert state.selected == 0
    state.selected = 4
    state.set_value("123,45")
    assert state.justified == D("123.45")
    state.set_value("aucun")
    assert state.justified is None
    state.adjust(1)
    assert state.justified == D("25")
    state.selected = 3
    state.set_value("4000,01")
    assert state.target == D("4000.01")
    state.selected = 6
    state.set_value("600")
    assert state.scenario.plafond_gestion == D("600")
    state.set_value("aucun")
    assert state.scenario.plafond_gestion is None
    state.selected = 21
    state.set_value("-25")
    assert state.scenario.ajustement == D("-25")
    state.selected = 1
    state.adjust(1, fine=True)
    assert state.scenario.jours == D("20.5")
    with pytest.raises(ValueError):
        Workshop(Scenario(), justified=D("-1"))


@given(st.text(max_size=50))
def test_edit_fuzz_is_bounded(text: str) -> None:
    state = Workshop(Scenario())
    try:
        state.set_value(text)
    except ValueError:
        assert state.scenario == Scenario()
    else:
        assert D("0") <= state.scenario.tjm <= D("1000000")


def test_advisory_boundaries_are_not_urssaf_audit_scores() -> None:
    s = Scenario(frais=D("500"), plafond_frais=D("100"), brut_minimum=D("1"))
    result = simulate(s)
    assert [a.level for a in assess(s, result, D("500"))] == ["INFO"]
    assert [a.level for a in assess(s, result, D("499.99"))] == ["ROUGE"]
    assert [a.level for a in assess(s, result, None)] == ["VIGILANCE"]
    assert assess(replace(s, frais=D("0")), result, D("0")) == []
    bad = replace(s, plafond_frais=D("1"), brut_minimum=D("10000"), teletravail=D("1"))
    alerts = assess(bad, simulate(bad, enforce=False), D("0"))
    assert [a.level for a in alerts] == ["ROUGE", "ROUGE", "ROUGE", "VIGILANCE"]
    with pytest.raises(ValueError):
        assess(s, result, D("-1"))


class Screen:
    """Fake terminal rejects drawing outside its dimensions and records visible content."""

    def __init__(self, keys: list[str | int] | None = None, size: tuple[int, int] = (24, 80)):
        self.keys = iter(keys or [])
        self.size = size
        self.lines: dict[int, str] = {}

    def getmaxyx(self) -> tuple[int, int]:
        return self.size

    def erase(self) -> None:
        self.lines = {}

    def refresh(self) -> None:
        pass

    def keypad(self, enabled: bool) -> None:
        assert enabled

    def addnstr(self, row: int, col: int, text: str, length: int, attr: int) -> None:
        assert 0 <= row < self.size[0]
        assert 0 <= col < self.size[1] - 1
        old = self.lines.get(row, " " * self.size[1])
        clipped = text[:length]
        self.lines[row] = old[:col] + clipped + old[col + len(clipped) :]

    def get_wch(self) -> str | int:
        return next(self.keys)


def test_keyboard_journey_and_layout() -> None:
    state = Workshop(Scenario(), D("4000"))
    screen: Any = Screen(
        [
            curses.KEY_RIGHT,
            "-",
            curses.KEY_DOWN,
            curses.KEY_UP,
            "\t",
            curses.KEY_BTAB,
            "\n",
            "4",
            "5",
            "0",
            "\n",
            "a",
            "f",
            "h",
            curses.KEY_DOWN,
            curses.KEY_UP,
            "h",
            "q",
        ]
    )
    interact(screen, state)
    assert state.scenario.tjm == D("450")
    assert state.snapshot()[0]["net_verse"] >= D("4000")
    assert "Virement après PAS" in screen.lines[4]
    assert "Salaire hors frais" in screen.lines[5]
    assert "€" in screen.lines[5]
    assert display(None) == "aucun"
    assert display(D("1234.56")) == "1 234,56"


@pytest.mark.parametrize("size", [(24, 80), (40, 120), (10, 30)])
def test_layout_sizes_and_invalid_budget(size: tuple[int, int]) -> None:
    state = Workshop(Scenario(frais=D("1000000")))
    screen: Any = Screen(["?", "h", curses.KEY_DOWN, "h", "q"], size=size)
    interact(screen, state)
    draw(screen, state, help_page=True, help_offset=100)
    write(screen, -1, 0, "outside")
    state.selected = 21
    state.set_value("-100")
    draw(screen, state)


def test_help_and_editing() -> None:
    state = Workshop(Scenario())
    screen: Any = Screen(["h", "?", "h", curses.KEY_LEFT, "+", "\n", "\x1b", "q"])
    interact(screen, state)
    assert state.scenario.tjm == D("495.01")
    screen = Screen(["1", "2", curses.KEY_BACKSPACE, "3", "\n"])
    assert read_value(screen, state) == "13"
    assert read_value(Screen([curses.KEY_RESIZE]), state) is None
    assert read_value(Screen(["x"] * 40 + ["\n"]), state) == "x" * 32


def test_terminal_cli_and_launch(monkeypatch: pytest.MonkeyPatch, capsys: Any) -> None:
    import sys

    assert main(["atelier"]) == 2
    assert "terminal interactif" in capsys.readouterr().err
    assert main(["atelier", "--json"]) == 2
    assert "interactif" in capsys.readouterr().err
    monkeypatch.setattr(sys.stdin, "isatty", lambda: True)
    monkeypatch.setattr(sys.stdout, "isatty", lambda: True)
    monkeypatch.setattr(curses, "wrapper", lambda callback, state: callback(Screen(["q"]), state))
    assert main(["atelier", "--net", "4500", "--frais-justifies", "100"]) == 0

    def interrupt(*args: object) -> None:
        raise KeyboardInterrupt

    monkeypatch.setattr(curses, "wrapper", interrupt)
    launch(Scenario(), D("4000"), None)

    def incompatible(*args: object) -> None:
        raise curses.error

    monkeypatch.setattr(curses, "wrapper", incompatible)
    assert main(["atelier"]) == 2
    assert "Terminal incompatible" in capsys.readouterr().err
    monkeypatch.setitem(sys.modules, "curses", None)
    with pytest.raises(ValueError, match="WSL"):
        launch(Scenario(), D("4000"), None)


def test_real_terminal_subprocess() -> None:
    """Real curses lifecycle, UTF-8 rendering, inverse target and clean terminal exit."""
    import os
    import pty
    import select
    import subprocess
    import sys
    import termios
    import time

    master, slave = pty.openpty()
    process = None
    try:
        termios.tcsetwinsize(slave, (24, 80))
        process = subprocess.Popen(
            [sys.executable, "-m", "portage", "atelier", "--jours", "22", "--tjm", "400"],
            stdin=slave,
            stdout=slave,
            stderr=slave,
            env={**os.environ, "TERM": "xterm-256color", "LC_ALL": "C.UTF-8"},
        )
        output = b""
        deadline = time.monotonic() + 5
        while b"ATELIER" not in output and time.monotonic() < deadline:
            ready, _, _ = select.select([master], [], [], 0.1)
            if ready:
                output += os.read(master, 65536)
        assert b"ATELIER" in output
        os.write(master, b"fhq")
        while process.poll() is None and time.monotonic() < deadline:
            ready, _, _ = select.select([master], [], [], 0.1)
            if ready:
                output += os.read(master, 65536)
        assert process.wait(timeout=2) == 0
        assert b"271,19" in output
        assert b"Traceback" not in output
    finally:
        if process is not None and process.poll() is None:
            process.kill()
            process.wait(timeout=2)
        os.close(master)
        os.close(slave)


def test_precise_control_values_remain_visible() -> None:
    from portage.terminal import control_display

    state = Workshop(Scenario(tjm=D("50000"), gestion=D("0.004")))
    screen: Any = Screen()
    draw(screen, state)
    assert "0,004" in screen.lines[9]
    assert state.snapshot()[0]["gestion"] == D("40.00")
    assert control_display(D("0.000001")) == "0,000001"
    assert control_display(D("1000000")) == "1 000 000"
    assert control_display(None) == "aucun"


def test_all_red_alerts_are_discoverable_at_minimum_size() -> None:
    scenario = Scenario(
        frais=D("500"), plafond_frais=D("1"), brut_minimum=D("10000"), teletravail=D("1")
    )
    state = Workshop(scenario, justified=D("0"))
    screen: Any = Screen()
    draw(screen, state)
    assert "3 ROUGE" in screen.lines[16]
    assert "Suite masquée" in screen.lines[19]
    assert "TOUTES les alertes" in screen.lines[19]
    draw(screen, state, help_page=True)
    text = " ".join(" ".join(screen.lines.values()).split())
    assert "justifiées déclarées" in text
    assert "Plafond contractuel" in text
    assert "minimum mensuel" in text
