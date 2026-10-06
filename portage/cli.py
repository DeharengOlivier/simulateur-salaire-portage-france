"""Interface francophone, profils TOML non exécutables et sorties JSON stables."""

import argparse
import json
import sys
import tomllib
from dataclasses import asdict, fields
from decimal import Decimal
from pathlib import Path
from typing import Any

from . import __version__
from .model import Scenario, reconcile, simulate, target_expenses
from .money import decimal

SCENARIO_FIELDS = {field.name for field in fields(Scenario)}
OPTIONAL_FIELDS = {"plafond_gestion", "plafond_frais", "taux_pas"}
LIMIT = 65536
NOTICE = (
    "Simulation à taux effectifs : calcul arrondi au centime, paie future non garantie. "
    "Renseigner les taux et régularisations propres à votre contrat."
)


def profile(path: Path) -> dict[str, Any]:
    with path.open("rb") as stream:
        raw = stream.read(LIMIT + 1)
    if len(raw) > LIMIT:
        raise ValueError("Profil trop volumineux (64 Kio maximum).")
    try:
        data = tomllib.loads(raw.decode("utf-8"))
    except RecursionError as exc:
        raise ValueError("Profil TOML trop profondément imbriqué.") from exc
    if set(data) != {"simulation"} or not isinstance(data["simulation"], dict):
        raise ValueError("Le profil doit contenir uniquement la table [simulation].")
    values = data["simulation"]
    if set(values) - SCENARIO_FIELDS:
        raise ValueError("Le profil contient un paramètre inconnu.")
    out: dict[str, Any] = {}
    for key, value in values.items():
        if key == "mois":
            if not isinstance(value, str):
                raise ValueError("mois doit être une chaîne AAAA-MM.")
            out[key] = value
        elif key in OPTIONAL_FIELDS and value == "aucun":
            out[key] = None
        else:
            out[key] = decimal(value)
    return out


def parse_number(text: str) -> Decimal:
    try:
        return decimal(text)
    except ValueError as exc:
        raise argparse.ArgumentTypeError(str(exc)) from exc


def optional_number(text: str) -> Decimal | None:
    return None if text == "aucun" else parse_number(text)


def options(parser: argparse.ArgumentParser) -> None:
    parser.add_argument("--profil", type=Path, help="profil TOML, surchargé par les options CLI")
    help_text = {
        "tjm": "tarif journalier HT (€)",
        "jours": "jours facturés, demi-journées admises",
        "frais": "frais remboursables non refacturés (€)",
        "gestion": "commission (%)",
        "plafond_gestion": "plafond mensuel de commission (€), ou aucun",
        "forfait_gestion": "forfait ajouté APRÈS le plafond (€)",
        "charges_patronales": "taux effectif patronal du brut (%)",
        "charges_salariales": "taux effectif salarié du brut, CSG incluse (%)",
        "csg_non_deductible": "part non déductible déjà incluse dans les charges (%) du brut",
        "reintegration_fiscale": "réintégrations fiscales complémentaires (€)",
        "taux_pas": "taux personnel (%), ou aucun pour le barème neutre",
        "teletravail": "indemnité totale du mois (€)",
        "titres": "nombre de titres-restaurant",
        "titre_salarie": "part salariale par titre (€)",
        "titre_employeur": "part patronale par titre (€)",
        "reserve": "montant supplémentaire placé en réserve (€)",
        "taux_reserve": "réserve (%) du CA après gestion",
        "ajustement": "ajustement signé du budget : solde, réserve débloquée, autres coûts (€)",
        "frais_refactures": "frais remboursés séparément par le client (€), hors commission",
        "plafond_frais": "limite (%) du brut pour les frais non refacturés, ou aucun",
        "brut_minimum": "minimum brut contractuel applicable au mois (€)",
        "mois": "mois de paie AAAA-MM ; défaut 2026-10, PAS neutre limité à mai-décembre 2026",
    }
    for field in fields(Scenario):
        parser.add_argument(
            "--" + field.name.replace("_", "-"),
            type=str
            if field.name == "mois"
            else (optional_number if field.name in OPTIONAL_FIELDS else parse_number),
            default=argparse.SUPPRESS,
            help=help_text[field.name].replace("%", "%%"),
        )
    parser.add_argument("--json", action="store_true", help="résultat et hypothèses en JSON")


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="portage",
        description="Simulateur de salaire en portage France — montants en euros.",
        epilog="Exemple : portage simuler --jours 22 --tjm 500 --frais 600 --gestion 5",
    )
    parser.add_argument("--version", action="version", version=__version__)
    commands = parser.add_subparsers(dest="command", required=True)
    sim = commands.add_parser("simuler", help="calculer un mois avec ses hypothèses")
    options(sim)
    target = commands.add_parser("objectif", help="chercher le minimum de frais pour un net cible")
    options(target)
    target.add_argument(
        "--net", type=parse_number, required=True, help="net viré cible après PAS (€)"
    )
    atelier = commands.add_parser("atelier", help="curseurs interactifs TJM / frais / objectif")
    options(atelier)
    atelier.add_argument(
        "--net",
        type=parse_number,
        default=Decimal("4000"),
        help="objectif de virement après PAS (€)",
    )
    atelier.add_argument(
        "--frais-justifies",
        type=parse_number,
        help="frais non refacturés réels et justifiés déclarés (€)",
    )
    init = commands.add_parser("profil", help="écrire un profil d'exemple sans écraser un fichier")
    init.add_argument("chemin", type=Path, nargs="?", default=Path("portage.local.toml"))
    replay = commands.add_parser("bulletin", help="recomposer le net à partir des totaux connus")
    for name in ("brut", "cotisations", "csg_non_deductible", "pas"):
        replay.add_argument("--" + name.replace("_", "-"), type=parse_number, required=True)
    for name in (
        "frais",
        "teletravail",
        "titres_salarie",
        "reintegration_fiscale",
        "autres_retenues",
        "autres_versements",
    ):
        replay.add_argument("--" + name.replace("_", "-"), type=parse_number, default=Decimal("0"))
    replay.add_argument("--net-attendu", type=parse_number, help="vérifier le net du bulletin (€)")
    replay.add_argument("--json", action="store_true")
    return parser


def example_profile() -> str:
    lines = [
        "# Taux effectifs ILLUSTRATIFS à remplacer par ceux de votre contrat.",
        "# Aucune donnée personnelle n'est fournie.",
        "[simulation]",
    ]
    for key, value in asdict(Scenario()).items():
        text = "aucun" if value is None else str(value)
        lines.append(f'{key} = "{text}"')
    return "\n".join(lines) + "\n"


def stringify(values: dict[str, Any]) -> dict[str, str | None]:
    return {key: None if value is None else str(value) for key, value in values.items()}


def output(result: dict[str, Decimal], args: argparse.Namespace, s: Scenario | None) -> None:
    mode = "simulation" if s else "reconstitution"
    notice = (
        NOTICE if s else "Reconstitution arithmétique des totaux fournis, sans audit de conformité."
    )
    if args.json:
        payload = {
            "version": __version__,
            "mode": mode,
            "avertissement": notice,
            "hypotheses": stringify(asdict(s)) if s else None,
            "resultat": stringify(result),
        }
        print(json.dumps(payload, ensure_ascii=False, indent=2))
        return
    print(f"\n{'SIMULATION' if s else 'BULLETIN'} — net versé : {result['net_verse']:,.2f} €\n")
    for key, value in result.items():
        unit = "%" if key == "taux_pas" else "€"
        print(f"  {key.replace('_', ' '):32} {value:>12,.2f} {unit}")
    print("\n" + notice)
    if s:
        print("Hypothèses : " + json.dumps(stringify(asdict(s)), ensure_ascii=False))


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    try:
        if args.command == "profil":
            # Exclusive creation: refuses existing files and symlinks. No hidden writes.
            with args.chemin.open("x", encoding="utf-8") as stream:
                stream.write(example_profile())
            print(f"Profil créé : {args.chemin}")
            return 0
        if args.command == "bulletin":
            keys = (
                "brut",
                "cotisations",
                "csg_non_deductible",
                "pas",
                "frais",
                "teletravail",
                "titres_salarie",
                "reintegration_fiscale",
                "autres_retenues",
                "autres_versements",
            )
            result = reconcile(**{key: getattr(args, key) for key in keys})
            if args.net_attendu is not None:
                from .money import amount

                result["ecart_net"] = result["net_verse"] - amount(args.net_attendu)
            output(result, args, None)
            return 1 if result.get("ecart_net", Decimal("0")) else 0
        values = profile(args.profil) if args.profil else {}
        values.update({key: value for key, value in vars(args).items() if key in SCENARIO_FIELDS})
        scenario = Scenario(**values)
        if args.command == "atelier":
            from .terminal import launch

            if args.json:
                raise ValueError(
                    "L'atelier est interactif ; utiliser simuler ou objectif avec --json."
                )
            launch(scenario, args.net, args.frais_justifies)
            return 0
        result = (
            target_expenses(scenario, args.net)
            if args.command == "objectif"
            else simulate(scenario)
        )
        output(result, args, scenario)
        return 0
    except (ValueError, OSError, UnicodeError) as exc:
        # Config errors do not echo user-controlled TOML contents or stack traces.
        if isinstance(exc, tomllib.TOMLDecodeError):
            detail = "Profil TOML invalide."
        elif isinstance(exc, OSError):
            detail = "Fichier inaccessible ou déjà existant."
        else:
            detail = str(exc)
        print(f"Erreur : {detail}", file=sys.stderr)
        return 2
