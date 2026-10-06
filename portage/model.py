"""Simulation mensuelle à taux effectifs et rapprochement à montants connus.

Les taux effectifs sont des hypothèses, jamais un moteur réglementaire de cotisations.
"""

from dataclasses import dataclass, replace
from decimal import Decimal

from .money import CENT, LIMIT, ZERO, amount, decimal, money, percent, rate
from .tax import withholding


@dataclass(frozen=True)
class Scenario:
    tjm: Decimal = Decimal("500")
    jours: Decimal = Decimal("20")
    frais: Decimal = ZERO
    gestion: Decimal = Decimal("5")
    plafond_gestion: Decimal | None = None
    forfait_gestion: Decimal = ZERO
    charges_patronales: Decimal = Decimal("45")
    charges_salariales: Decimal = Decimal("22")
    csg_non_deductible: Decimal = Decimal("2.85")
    reintegration_fiscale: Decimal = ZERO
    taux_pas: Decimal | None = None
    teletravail: Decimal = ZERO
    titres: Decimal = ZERO
    titre_salarie: Decimal = Decimal("7.50")
    titre_employeur: Decimal = Decimal("7.50")
    reserve: Decimal = ZERO
    taux_reserve: Decimal = ZERO
    ajustement: Decimal = ZERO
    frais_refactures: Decimal = ZERO
    plafond_frais: Decimal | None = None
    brut_minimum: Decimal = ZERO
    mois: str = "2026-10"

    def __post_init__(self) -> None:
        for name in (
            "tjm",
            "frais",
            "forfait_gestion",
            "reintegration_fiscale",
            "teletravail",
            "titre_salarie",
            "titre_employeur",
            "reserve",
            "frais_refactures",
            "brut_minimum",
        ):
            amount(getattr(self, name))
        amount(self.ajustement, signed=True)
        if self.plafond_gestion is not None:
            amount(self.plafond_gestion)
        for name in (
            "gestion",
            "charges_patronales",
            "charges_salariales",
            "csg_non_deductible",
            "taux_reserve",
        ):
            rate(getattr(self, name))
        for value in (self.taux_pas, self.plafond_frais):
            if value is not None:
                rate(value)
        if self.csg_non_deductible > self.charges_salariales:
            raise ValueError("La CSG non déductible est comprise dans les charges salariales.")
        if not ZERO <= decimal(self.jours) <= 31 or self.jours * 2 % 1:
            raise ValueError("Jours : de 0 à 31, par demi-journée.")
        if not ZERO <= decimal(self.titres) <= self.jours or self.titres % 1:
            raise ValueError("Titres : nombre entier de 0 au nombre de jours travaillés.")
        import datetime

        try:
            date = datetime.date.fromisoformat(self.mois + "-01")
        except ValueError as exc:
            raise ValueError("Mois attendu au format AAAA-MM.") from exc
        if self.taux_pas is None and not (date.year == 2026 and date.month >= 5):
            raise ValueError("PAS neutre disponible de mai à décembre 2026 ; fournir --taux-pas.")


def budget(s: Scenario) -> dict[str, Decimal]:
    ca = money(s.tjm * s.jours)
    if ca > Decimal("1000000"):
        raise ValueError("Chiffre d'affaires mensuel limité à 1 000 000 €.")
    commission = percent(ca, s.gestion)
    if s.plafond_gestion is not None:
        commission = min(commission, s.plafond_gestion)
    gestion = commission + s.forfait_gestion
    reserve = s.reserve + percent(ca - gestion, s.taux_reserve)
    available = ca - gestion - reserve + s.ajustement
    if ca < gestion or available < ZERO:
        raise ValueError("Gestion ou réserve supérieure au budget disponible.")
    return {"chiffre_affaires": ca, "gestion": gestion, "reserve": reserve, "budget": available}


def gross_for_budget(available: Decimal, employer_rate: Decimal) -> Decimal:
    """Plus grand brut au centime dont le coût arrondi tient dans l'enveloppe."""
    low, high = 0, int(available / CENT)
    while low < high:
        mid = (low + high + 1) // 2
        gross = Decimal(mid) * CENT
        if gross + percent(gross, employer_rate) <= available:
            low = mid
        else:
            high = mid - 1
    return Decimal(low) * CENT


def simulate(s: Scenario, *, enforce: bool = True) -> dict[str, Decimal]:
    out = budget(s)
    employer_meals = money(s.titres * s.titre_employeur)
    employee_meals = money(s.titres * s.titre_salarie)
    available = out["budget"] - s.frais - s.teletravail - employer_meals
    if available < ZERO:
        raise ValueError("Les frais et avantages dépassent le budget.")
    gross = gross_for_budget(available, s.charges_patronales)
    if enforce and gross < s.brut_minimum:
        raise ValueError("Le brut calculé est inférieur au minimum configuré.")
    # Plafond conservateur : jamais un centime au-dessus du pourcentage exact.
    cap = (gross * s.plafond_frais / 100 // CENT) * CENT if s.plafond_frais is not None else None
    if enforce and cap is not None and s.frais > cap:
        raise ValueError(f"Frais supérieurs au plafond configuré ({cap:.2f} €).")
    employer = percent(gross, s.charges_patronales)
    employee = percent(gross, s.charges_salariales)
    social = gross - employee
    nondeductible = percent(gross, s.csg_non_deductible)
    taxable = social + nondeductible + s.reintegration_fiscale
    pas, pas_rate = withholding(taxable, s.taux_pas)
    before = social + s.frais + s.frais_refactures + s.teletravail - employee_meals
    out.update(
        {
            "brut": gross,
            "cotisations_patronales": employer,
            "cotisations_salariales": employee,
            "csg_non_deductible": nondeductible,
            "reintegration_fiscale": s.reintegration_fiscale,
            "net_salarial_avant_pas": social,
            "net_imposable": taxable,
            "frais": s.frais,
            "frais_refactures": s.frais_refactures,
            "teletravail": s.teletravail,
            "titres_salarie": employee_meals,
            "titres_employeur": employer_meals,
            "net_avant_pas": before,
            "taux_pas": pas_rate,
            "pas": pas,
            "net_verse": before - pas,
            "solde_budget": available - gross - employer,
        }
    )
    return out


def target_expenses(s: Scenario, target: Decimal) -> dict[str, Decimal]:
    """Minimum de frais en centimes dans le modèle agrégé, contraintes incluses.

    À chaque centime de frais, le brut baisse de 0 ou 1 centime. Le net salarial
    et la base PAS baissent de façon monotone (un seul arrondi de cotisations).
    Le net versé est donc non décroissant ; le domaine admissible est un préfixe.
    Cette propriété ne s'étend PAS à un modèle de cotisations arrondies ligne par ligne.
    """
    amount(target)
    base = replace(s, frais=ZERO)
    start = simulate(base)
    limit = budget(base)["budget"] - base.teletravail - money(base.titres * base.titre_employeur)
    low, high = 0, int(min(limit, LIMIT) / CENT)
    while low < high:
        mid = (low + high + 1) // 2
        candidate = replace(base, frais=Decimal(mid) * CENT)
        result = simulate(candidate, enforce=False)
        gross = result["brut"]
        valid = gross >= s.brut_minimum and (
            s.plafond_frais is None or candidate.frais <= gross * s.plafond_frais / 100
        )
        if valid:
            low = mid
        else:
            high = mid - 1
    max_expenses = Decimal(low) * CENT
    maximum = simulate(replace(base, frais=max_expenses))
    if maximum["net_verse"] < target:
        raise ValueError(
            f"Objectif inaccessible : maximum {maximum['net_verse']:.2f} € "
            f"pour {max_expenses:.2f} € de frais, avec ces contraintes."
        )
    low, high = 0, low
    while low < high:
        mid = (low + high) // 2
        if simulate(replace(base, frais=Decimal(mid) * CENT))["net_verse"] >= target:
            high = mid
        else:
            low = mid + 1
    result = start if low == 0 else simulate(replace(base, frais=Decimal(low) * CENT))
    result["objectif"] = target
    result["frais_supplementaires"] = max(ZERO, result["frais"] - s.frais)
    return result


def reconcile(
    *,
    brut: Decimal,
    cotisations: Decimal,
    csg_non_deductible: Decimal,
    pas: Decimal,
    frais: Decimal = ZERO,
    teletravail: Decimal = ZERO,
    titres_salarie: Decimal = ZERO,
    reintegration_fiscale: Decimal = ZERO,
    autres_retenues: Decimal = ZERO,
    autres_versements: Decimal = ZERO,
) -> dict[str, Decimal]:
    """Recomposition arithmétique exacte à partir des totaux du bulletin fourni."""
    values = (
        brut,
        cotisations,
        csg_non_deductible,
        pas,
        frais,
        teletravail,
        titres_salarie,
        reintegration_fiscale,
        autres_retenues,
        autres_versements,
    )
    for value in values:
        amount(value)
    if cotisations > brut or csg_non_deductible > cotisations:
        raise ValueError("Cotisations / CSG incohérentes avec le brut.")
    social = brut - cotisations
    before = social + frais + teletravail + autres_versements - titres_salarie - autres_retenues
    return {
        "brut": brut,
        "cotisations_salariales": cotisations,
        "net_salarial_avant_pas": social,
        "net_imposable": social + csg_non_deductible + reintegration_fiscale,
        "frais": frais,
        "teletravail": teletravail,
        "titres_salarie": titres_salarie,
        "csg_non_deductible": csg_non_deductible,
        "reintegration_fiscale": reintegration_fiscale,
        "autres_retenues": autres_retenues,
        "autres_versements": autres_versements,
        "net_avant_pas": before,
        "pas": pas,
        "net_verse": before - pas,
    }
