"""Rendu curses uniquement ; aucune formule monétaire dans l'interface."""

import sys
import textwrap
from decimal import Decimal
from typing import TYPE_CHECKING

from .atelier import CONTROLS, Workshop
from .model import Scenario

if TYPE_CHECKING:
    import curses


def display(value: Decimal | None) -> str:
    return "aucun" if value is None else f"{value:,.2f}".replace(",", " ").replace(".", ",")


def control_display(value: Decimal | None) -> str:
    if value is None:
        return "aucun"
    return f"{value:,.6f}".rstrip("0").rstrip(".").replace(",", " ").replace(".", ",")


def write(screen: "curses.window", row: int, col: int, text: str, attr: int = 0) -> None:
    height, width = screen.getmaxyx()
    if 0 <= row < height and 0 <= col < width - 1:
        screen.addnstr(row, col, text, width - col - 1, attr)


def draw(
    screen: "curses.window", state: Workshop, *, help_page: bool = False, help_offset: int = 0
) -> None:
    import curses

    screen.erase()
    height, width = screen.getmaxyx()
    write(screen, 0, 0, "PORTAGE / ATELIER DE RÉMUNÉRATION", curses.A_BOLD)
    if width < 80 or height < 24:
        write(screen, 2, 0, "Agrandir à 80 colonnes × 24 lignes. Q : quitter.")
        screen.refresh()
        return
    if help_page:
        help_lines = [
            "REPÈRES URSSAF — pas de score de suspicion ni de garantie de conformité",
            "Les frais réels doivent correspondre à des dépenses "
            "professionnelles et être justifiés. Le montant déclaré ici n'est "
            "pas une vérification des pièces.",
            "Les forfaits ont des conditions et barèmes propres : dépasser un "
            "forfait ne signifie pas automatiquement fraude. Cet outil ne "
            "valide pas ces régimes.",
            "ROUGE : frais supérieurs au montant justifié déclaré, plafond "
            "contractuel dépassé ou brut inférieur au minimum configuré.",
            "VIGILANCE : éléments manquants ou autres indemnités à vérifier. "
            "Aucun pourcentage de frais n'est présenté comme un seuil "
            "universel de contrôle Urssaf.",
            "L'objectif porte sur le virement après PAS, remboursements "
            "inclus. Le salaire hors remboursements apparaît séparément. Les "
            "frais ne sont pas un gain équivalent à du salaire.",
            "F cherche le minimum mathématique de frais, sous les plafonds et "
            "minimum brut configurés. Cette proposition n'autorise pas de "
            "dépenses fictives.",
            "Barème neutre : mai-décembre 2026. Les taux effectifs restent "
            "des hypothèses ; la paie future n'est pas garantie au centime.",
            "Source Urssaf, consultée le 06/10/2026 : voir README, section Atelier. H : revenir.",
        ]
        try:
            _, checks = state.snapshot()
            help_lines = [f"{a.level} — {a.message}" for a in checks] + help_lines
        except ValueError as exc:
            help_lines.insert(0, "ROUGE — " + str(exc))
        lines: list[str] = []
        for paragraph in help_lines:
            lines.extend(textwrap.wrap(paragraph, width - 2) + [""])
        offset = min(help_offset, max(0, len(lines) - height + 5))
        for row, line in enumerate(lines[offset : offset + height - 5], 2):
            write(screen, row, 0, line)
        write(screen, height - 2, 0, "↑↓ défiler · H revenir · Q quitter")
        screen.refresh()
        return
    write(
        screen,
        1,
        0,
        f"{state.scenario.mois} · estimation à taux effectifs · hors ligne · rien n'est enregistré",
    )
    write(screen, 3, 0, "PARAMÈTRES  ↑↓ / Tab", curses.A_BOLD)
    first = max(0, min(state.selected - 3, len(CONTROLS) - 7))
    for index, item in enumerate(CONTROLS[first : first + 7], first):
        label = f"{item.label[:24]:24} {control_display(state.value(item)):>9}"
        write(
            screen,
            4 + index - first,
            0,
            label[:40],
            curses.A_REVERSE if index == state.selected else 0,
        )
    value = state.value(state.current) or Decimal("0")
    visual_max = min(state.current.maximum, max(Decimal("1000"), abs(value) * 2))
    if state.current.minimum < 0:
        visual_min = -visual_max
    else:
        visual_min = Decimal("0")
    position = int((value - visual_min) / (visual_max - visual_min) * 26)
    bar = "─" * position + "●" + "─" * (26 - position)
    write(screen, 12, 0, f"← {bar} →")
    write(screen, 13, 0, f"Échelle {display(visual_min)} à {display(visual_max)}")
    write(screen, 14, 0, f"Pas {display(state.current.step)} ; +/- : fin")
    write(screen, 3, 42, "PROJECTION DU MOIS", curses.A_BOLD)
    alerts: list[tuple[str, str]] = []
    try:
        result, checks = state.snapshot()
        reimbursements = result["frais"] + result["frais_refactures"] + result["teletravail"]
        rows = [
            ("Virement après PAS", result["net_verse"]),
            ("Salaire hors frais", result["net_verse"] - reimbursements),
            ("Remboursements", reimbursements),
            ("Écart objectif", result["net_verse"] - state.target),
            ("Brut", result["brut"]),
            ("Commission + forfait", result["gestion"]),
            ("PAS", result["pas"]),
            ("CA HT", result["chiffre_affaires"]),
        ]
        for index, (label, total) in enumerate(rows):
            write(
                screen,
                4 + index,
                42,
                f"{label}: {display(total)} €",
                curses.A_BOLD if index == 0 else 0,
            )
        alerts = [(alert.level, alert.message) for alert in checks]
    except ValueError as exc:
        write(screen, 5, 42, "CALCUL IMPOSSIBLE", curses.A_BOLD)
        alerts = [("ROUGE", str(exc))]
    alerts.sort(key=lambda alert: {"ROUGE": 0, "VIGILANCE": 1, "INFO": 2}[alert[0]])
    red_count = sum(level == "ROUGE" for level, _ in alerts)
    warning_count = sum(level == "VIGILANCE" for level, _ in alerts)
    write(
        screen,
        16,
        0,
        f"REPÈRES : {red_count} ROUGE · {warning_count} VIGILANCE · H : toutes les alertes",
        curses.A_BOLD,
    )
    alert_lines = [
        (level, line)
        for level, message in alerts
        for line in textwrap.wrap(f"{level} — {message}", width - 2)
    ]
    available_lines = height - 21
    overflow = len(alert_lines) > available_lines
    visible_lines = available_lines - int(overflow)
    for row, (level, line) in enumerate(alert_lines[:visible_lines], 17):
        write(screen, row, 0, line, curses.A_BOLD if level == "ROUGE" else 0)
    if overflow:
        write(
            screen,
            height - 5,
            0,
            "… Suite masquée : H pour lire TOUTES les alertes.",
            curses.A_BOLD,
        )
    status_lines = textwrap.wrap(state.status, width - 2)
    for offset, line in enumerate(status_lines[:2]):
        write(screen, height - 4 + offset, 0, line)
    write(
        screen,
        height - 2,
        0,
        "←→ ajuster · Entrée saisir · A aucun · F objectif · H aide · Q quitter",
    )
    screen.refresh()


def read_value(screen: "curses.window", state: Workshop) -> str | None:
    import curses

    value = ""
    while True:
        draw(screen, state)
        write(screen, screen.getmaxyx()[0] - 3, 0, "Saisie (Échap annule) : " + value + "_")
        screen.refresh()
        key = screen.get_wch()
        if key in ("\x1b", curses.KEY_RESIZE):
            return None
        if key in ("\n", "\r", curses.KEY_ENTER):
            return value
        if key in ("\b", "\x7f", curses.KEY_BACKSPACE):
            value = value[:-1]
        elif isinstance(key, str) and key.isprintable() and len(value) < 32:
            value += key


def interact(screen: "curses.window", state: Workshop) -> None:
    import curses

    screen.keypad(True)
    help_page = False
    help_offset = 0
    while True:
        draw(screen, state, help_page=help_page, help_offset=help_offset)
        key = screen.get_wch()
        if key in ("q", "Q", "\x1b"):
            return
        if key in ("h", "H"):
            help_page = not help_page
            continue
        height, width = screen.getmaxyx()
        if help_page:
            if key == curses.KEY_DOWN:
                help_offset = min(100, help_offset + 1)
            elif key == curses.KEY_UP:
                help_offset = max(0, help_offset - 1)
            continue
        if height < 24 or width < 80:
            continue
        try:
            if key in (curses.KEY_UP, curses.KEY_BTAB):
                state.move(-1)
            elif key in (curses.KEY_DOWN, "\t"):
                state.move(1)
            elif key in (curses.KEY_LEFT, "-"):
                state.adjust(-1, fine=key == "-")
            elif key in (curses.KEY_RIGHT, "+"):
                state.adjust(1, fine=key == "+")
            elif key in ("a", "A"):
                state.set_value("aucun")
            elif key in ("f", "F"):
                state.solve()
            elif key in ("\n", "\r", curses.KEY_ENTER):
                value = read_value(screen, state)
                if value is not None:
                    state.set_value(value)
        except ValueError as exc:
            state.status = "Saisie refusée : " + str(exc)


def launch(scenario: Scenario, target: Decimal, justified: Decimal | None) -> None:
    if not sys.stdin.isatty() or not sys.stdout.isatty():
        raise ValueError(
            "L'atelier exige un terminal interactif. Utiliser simuler --json en script."
        )
    try:
        import curses
    except ImportError as exc:
        raise ValueError(
            "Atelier disponible sous macOS/Linux avec curses (Windows : utiliser WSL)."
        ) from exc
    state = Workshop(scenario, target, justified)
    try:
        curses.wrapper(interact, state)
    except curses.error as exc:
        raise ValueError(
            "Terminal incompatible ; vérifier TERM et une taille minimale de 80 × 24."
        ) from exc
    except KeyboardInterrupt:
        pass  # User-requested exit; wrapper restores the terminal.
