"""Repères documentaires et contractuels, jamais un score de contrôle Urssaf."""

from dataclasses import dataclass
from decimal import Decimal

from .model import Scenario
from .money import ZERO, amount

SOURCE = "https://www.urssaf.fr/accueil/employeur/beneficier-exonerations/frais-professionnels.html"


@dataclass(frozen=True)
class Alert:
    level: str
    message: str


def assess(
    scenario: Scenario, result: dict[str, Decimal], justified: Decimal | None
) -> list[Alert]:
    """justified = frais NON refacturés réellement professionnels et justifiés déclarés.

    Ce montant est une déclaration de l'utilisateur, pas une vérification de pièces.
    Aucun ratio n'est assimilé à une probabilité de contrôle ou à un seuil légal.
    """
    alerts: list[Alert] = []
    if justified is not None:
        amount(justified)
    if scenario.frais > ZERO:
        if justified is None:
            alerts.append(
                Alert(
                    "VIGILANCE",
                    "Frais réels justifiés non renseignés : vérifier les "
                    "pièces et le lien professionnel.",
                )
            )
        elif scenario.frais > justified:
            alerts.append(
                Alert(
                    "ROUGE",
                    "Frais simulés supérieurs aux dépenses professionnelles justifiées déclarées.",
                )
            )
        else:
            alerts.append(
                Alert(
                    "INFO",
                    "Frais couverts par votre déclaration de justificatifs ; pièces non vérifiées.",
                )
            )
    if scenario.plafond_frais is None:
        alerts.append(
            Alert(
                "VIGILANCE",
                "Plafond contractuel des frais non renseigné ; aucun seuil "
                "Urssaf universel n'est appliqué.",
            )
        )
    elif scenario.frais > result["brut"] * scenario.plafond_frais / 100:
        alerts.append(
            Alert(
                "ROUGE",
                "Plafond contractuel configuré dépassé (pourcentage du brut, pas un seuil Urssaf).",
            )
        )
    if result["brut"] < scenario.brut_minimum:
        alerts.append(Alert("ROUGE", "Brut inférieur au minimum mensuel configuré."))
    elif scenario.brut_minimum == ZERO:
        alerts.append(
            Alert(
                "VIGILANCE",
                "Minimum brut non renseigné : vérifier le contrat et le "
                "minimum conventionnel applicable.",
            )
        )
    if scenario.frais_refactures or scenario.teletravail or scenario.titres:
        alerts.append(
            Alert(
                "VIGILANCE",
                "Télétravail, titres et frais refacturés : vérifier les "
                "conditions propres et éviter les doubles remboursements.",
            )
        )
    return alerts
