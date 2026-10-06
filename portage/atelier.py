"""Atelier terminal : état testable, mêmes calculs Decimal que le CLI."""

from dataclasses import dataclass, replace
from decimal import Decimal
from typing import Any, cast

from .advisory import Alert, assess
from .model import Scenario, simulate, target_expenses
from .money import ZERO, amount, decimal


@dataclass(frozen=True)
class Control:
    key: str
    label: str
    step: Decimal
    maximum: Decimal
    optional: bool = False
    minimum: Decimal = ZERO


def control(
    key: str, label: str, step: str, maximum: str = "1000000", optional: bool = False
) -> Control:
    return Control(key, label, Decimal(step), Decimal(maximum), optional)


CONTROLS = (
    control("tjm", "TJM HT (€)", "5"),
    control("jours", "Jours facturés", "0.5", "31"),
    control("frais", "Frais non refacturés (€)", "25"),
    control("target", "Objectif VIRÉ après PAS (€)", "50"),
    control("justified", "Frais réels justifiés (€)", "25", optional=True),
    control("gestion", "Commission (%)", "0.5", "100"),
    control("plafond_gestion", "Plafond commission (€)", "25", optional=True),
    control("forfait_gestion", "Forfait gestion (€)", "5"),
    control("plafond_frais", "Plafond frais (% brut)", "1", "100", optional=True),
    control("brut_minimum", "Minimum brut du mois (€)", "50"),
    control("charges_patronales", "Charges employeur (%)", "0.1", "100"),
    control("charges_salariales", "Charges salarié (%)", "0.1", "100"),
    control("csg_non_deductible", "CSG non déductible (%)", "0.01", "100"),
    control("taux_pas", "PAS (%) / neutre si aucun", "0.1", "100", optional=True),
    control("reintegration_fiscale", "Réintégration fiscale (€)", "5"),
    control("teletravail", "Télétravail total (€)", "1"),
    control("titres", "Titres-restaurant (nombre)", "1", "31"),
    control("titre_salarie", "Part titre salarié (€)", "0.1"),
    control("titre_employeur", "Part titre employeur (€)", "0.1"),
    control("reserve", "Réserve fixe (€)", "25"),
    control("taux_reserve", "Réserve (%)", "1", "100"),
    Control(
        "ajustement",
        "Ajustement budget (€)",
        Decimal("25"),
        Decimal("1000000"),
        minimum=Decimal("-1000000"),
    ),
    control("frais_refactures", "Frais refacturés (€)", "25"),
)


@dataclass
class Workshop:
    scenario: Scenario
    target: Decimal = Decimal("4000")
    justified: Decimal | None = None
    selected: int = 0
    status: str = "Hypothèses illustratives. ↑↓ choisir, ←→ ajuster, Entrée saisir."

    def __post_init__(self) -> None:
        amount(self.target)
        if self.justified is not None:
            amount(self.justified)

    @property
    def current(self) -> Control:
        return CONTROLS[self.selected]

    def value(self, item: Control) -> Decimal | None:
        if item.key in {"target", "justified"}:
            return getattr(self, item.key)  # type: ignore[no-any-return]
        return getattr(self.scenario, item.key)  # type: ignore[no-any-return]

    def set_value(self, text: str) -> None:
        item = self.current
        value = None if item.optional and text.strip().lower() == "aucun" else decimal(text)
        if value is not None and not item.minimum <= value <= item.maximum:
            raise ValueError("Valeur hors des limites du paramètre.")
        if item.key in {"target", "justified"}:
            if value is not None:
                amount(value)
            setattr(self, item.key, value)
        else:
            self.scenario = replace(self.scenario, **cast(dict[str, Any], {item.key: value}))
        self.status = "Paramètre actualisé ; aucune donnée enregistrée."

    def move(self, direction: int) -> None:
        self.selected = (self.selected + direction) % len(CONTROLS)

    def adjust(self, direction: int, *, fine: bool = False) -> None:
        item = self.current
        step = Decimal("0.01") if fine and item.key not in {"jours", "titres"} else item.step
        value = self.value(item)
        updated = max(item.minimum, min(item.maximum, (value or ZERO) + step * direction))
        self.set_value(str(updated))

    def snapshot(self) -> tuple[dict[str, Decimal], list[Alert]]:
        # Deliberately show invalid contractual scenarios with RED alerts, never silently accept.
        result = simulate(self.scenario, enforce=False)
        return result, assess(self.scenario, result, self.justified)

    def solve(self) -> None:
        result = target_expenses(self.scenario, self.target)
        self.scenario = replace(self.scenario, frais=result["frais"])
        self.selected = 2
        self.status = "Minimum mathématique appliqué. Dépenses réelles et justificatifs à vérifier."
