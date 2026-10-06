"""Validation et arrondis monétaires : aucun flottant binaire dans les calculs."""

from decimal import ROUND_HALF_UP, Decimal, InvalidOperation

CENT = Decimal("0.01")
ZERO = Decimal("0")
HUNDRED = Decimal("100")
LIMIT = Decimal("1000000")


def decimal(value: object) -> Decimal:
    if isinstance(value, bool) or not isinstance(value, (str, int, Decimal)):
        raise ValueError("Utiliser un nombre entier ou une chaîne décimale (pas de float).")
    text = str(value).strip().replace(",", ".")
    if len(text) > 32:
        raise ValueError("Nombre trop long.")
    try:
        number = Decimal(text)
    except InvalidOperation as exc:
        raise ValueError("Nombre décimal invalide.") from exc
    exponent = number.as_tuple().exponent
    if (
        not number.is_finite()
        or abs(number) > LIMIT
        or not isinstance(exponent, int)
        or exponent < -6
    ):
        raise ValueError("Nombre hors limites : fini, ±1 000 000, six décimales maximum.")
    return number


def money(value: Decimal) -> Decimal:
    return value.quantize(CENT, rounding=ROUND_HALF_UP)


def percent(base: Decimal, rate: Decimal) -> Decimal:
    return money(base * rate / HUNDRED)


def amount(value: object, *, signed: bool = False) -> Decimal:
    number = decimal(value)
    if (not signed and number < ZERO) or money(number) != number:
        raise ValueError("Montant invalide : positif ou nul, deux décimales maximum.")
    return money(number)


def rate(value: object) -> Decimal:
    number = decimal(value)
    if not ZERO <= number <= HUNDRED:
        raise ValueError("Le taux doit être compris entre 0 et 100 (5 signifie 5 %).")
    return number
