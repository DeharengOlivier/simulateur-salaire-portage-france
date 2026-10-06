"""PAS mensuel métropole / hors France, grille BOFiP du 6 juillet 2026."""

from decimal import Decimal

from .money import percent

# Seuil supérieur exclusif, taux en pourcentage. Aucun seuil déduit d'un bulletin privé.
BRACKETS = tuple(
    (Decimal(cap), Decimal(value))
    for cap, value in (
        ("1635", "0"),
        ("1698", "0.5"),
        ("1807", "1.3"),
        ("1928", "2.1"),
        ("2060", "2.9"),
        ("2170", "3.5"),
        ("2315", "4.1"),
        ("2738", "5.3"),
        ("3135", "7.5"),
        ("3571", "9.9"),
        ("4019", "11.9"),
        ("4690", "13.8"),
        ("5624", "15.8"),
        ("7037", "17.9"),
        ("8789", "20"),
        ("12200", "24"),
        ("16523", "28"),
        ("25937", "33"),
        ("55558", "38"),
    )
)


def neutral_rate(taxable: Decimal) -> Decimal:
    return next((value for cap, value in BRACKETS if taxable < cap), Decimal("43"))


def withholding(taxable: Decimal, personal_rate: Decimal | None) -> tuple[Decimal, Decimal]:
    selected = neutral_rate(taxable) if personal_rate is None else personal_rate
    return percent(taxable, selected), selected
