# Simulateur de salaire en portage France

Un CLI en français pour comparer des contrats de portage, simuler un mois et chercher les frais nécessaires à un net cible. **Calculs décimaux et arrondis au centime, sans dépendance à l'exécution, sans réseau.**

> La précision arithmétique n'est pas une garantie de paie. Une simulation utilise vos **taux effectifs** : elle ne remplace pas le calcul réglementaire des cotisations, de leurs tranches et des régularisations annuelles. La commande `bulletin` recompose exactement le net à partir des montants déjà connus. Aucun profil de société n'est certifié.

## Installation

Python 3.12 ou plus récent. Avec [uv](https://docs.astral.sh/uv/), une fois ce dépôt publié :

```sh
uv tool install git+https://github.com/DeharengOlivier/simulateur-salaire-portage-france.git
portage --help
```

Ou depuis le dépôt cloné, sans installation ni dépendance :

```sh
python3 -m portage simuler --jours 22 --tjm 500 --frais 600
```

## Trois commandes utiles

### 1. Calculer un mois

```sh
portage simuler --jours 22 --tjm 500 --frais 600 --gestion 5 --plafond-gestion 600
```

Une commission de 5 %, plafonnée à 600 € **par mois**. Retirer le plafond avec `--plafond-gestion aucun`. Un éventuel `--forfait-gestion 50` est ajouté **après** ce plafond. Les montants de frais sont les montants **remboursables**, pas nécessairement le TTC de la facture.

```sh
portage simuler --jours 20 --tjm 450 --frais 700 \
  --charges-patronales 40 --charges-salariales 21 \
  --csg-non-deductible 2,85 --taux-pas 7,5 \
  --titres 18 --titre-salarie 7,50 --titre-employeur 7,50 \
  --teletravail 45 --reserve 100 --taux-reserve 10
```

Les deux parts des titres-restaurant sont prises en compte : l'une réduit le budget de salaire, l'autre le virement. Le PAS utilise un taux personnel si fourni, sinon la grille mensuelle métropole/hors France **mai-décembre 2026**. `--mois` désigne le mois auquel la grille s'applique, par défaut `2026-10`. Hors de cette période, un taux personnel explicite est requis. Outre-mer, contrat court, base PAS spéciale : calcul automatique non pris en charge.

### 2. Atteindre un objectif

```sh
portage objectif --net 4000 --jours 22 --tjm 500 --gestion 5 \
  --plafond-gestion 600 --plafond-frais 25 --brut-minimum 3500
```

Recherche le **premier centime** de frais atteignant au moins le net cible, dans le modèle et les contraintes configurées. Le plafond des frais est un **pourcentage du brut**, celui de la gestion un **montant en euros**. Un objectif inaccessible produit une erreur explicite et le maximum possible. `--frais 500` indique le montant déjà prévu, pour afficher le complément nécessaire. Le simulateur n'invente pas de dépenses : il faut des frais réels remboursables.

Les minima conventionnels et plafonds contractuels doivent être renseignés ; aucune limite légale ou spécifique à une société n'est inférée. Un résultat mathématiquement possible ne valide pas la conformité du montage.

### 3. Vérifier un bulletin au centime

Exemple entièrement fictif :

```sh
portage bulletin --brut 3000 --cotisations 630 --csg-non-deductible 85,50 \
  --frais 400 --teletravail 40 --titres-salarie 120 --pas 130 \
  --net-attendu 2560
```

Renvoie un écart nul et un code de sortie 0. Un écart renvoie 1. Utiliser `--reintegration-fiscale`, `--autres-retenues` et `--autres-versements` si le bulletin comporte d'autres éléments. On fournit ici les **totaux exacts de paie**, pas des taux approximatifs. La CSG non déductible est déjà comprise dans les cotisations : elle s'ajoute au net imposable, pas au net payé.

## Garder son profil

```sh
portage profil
# Éditer portage.local.toml avec ses paramètres.
portage simuler --profil portage.local.toml --jours 22 --json
portage objectif --profil portage.local.toml --net 4000
```

Le fichier créé documente tous les paramètres, les options de commande le surchargent. Les fichiers `*.local.toml` et le répertoire `private/` sont ignorés par Git. Un profil existant n'est jamais écrasé. Les décimales TOML s'écrivent **entre guillemets** (`gestion = "5.5"`) pour ne pas passer par des flottants binaires. Les virgules sont acceptées dans le CLI. Chaque sortie indique les hypothèses utilisées ; le JSON encode les montants comme des chaînes décimales.

## Ce qui est calculé

1. CA HT = TJM × jours. Commission = min(CA × taux, plafond éventuel), puis forfait.
2. Réserve = montant fixe + pourcentage du CA après gestion. `--ajustement` ajoute ou retranche un montant au budget (régularisation, réserve débloquée, autre prélèvement).
3. Déduction des frais, de l'indemnité télétravail et des titres employeur.
4. Recherche du plus grand brut au centime dont **brut + charges patronales arrondies** tient dans l'enveloppe. Le reliquat est affiché.
5. Cotisations salarié, net imposable, PAS, puis net versé après frais, indemnités et part salarié des titres.

`--frais-refactures` représente un remboursement client **séparé** : ajouté au virement sans réduire le budget salarial, sans gestion dessus. Si votre contrat prélève une commission sur ces frais, intégrer ce coût dans `--ajustement`. Aucune gestion de TVA n'est réalisée. Les remboursements de dépenses ne sont pas un enrichissement équivalent à du salaire.

Tous les produits monétaires sont arrondis à 0,01 € en `ROUND_HALF_UP`. Chaque ligne agrégée est arrondie séparément. Les cotisations ne sont pas ventilées par caisse : les taux effectifs peuvent changer avec le brut et le cumul annuel. Les congés payés et la prime d'apport sont supposés déjà compris dans le brut global, pas versés une seconde fois. Le net salarial avant PAS n'est pas présenté comme le « montant net social » réglementaire.

## Sources et limites

- [PAS : BOFiP du 6 juillet 2026](https://bofip.impots.gouv.fr/bofip/11255-PGP.html/identifiant=BOI-BAREME-000037-20260706) : grille utilisée, seuils et arrondis couverts par les tests.
- [Urssaf : calcul des cotisations](https://www.urssaf.fr/accueil/employeur/cotisations/comprendre-cotisations/calcul-cotisations-employeur.html) : assiettes, plafonds et régularisations justifient l'utilisation prudente de taux effectifs.
- [Service Public : portage salarial](https://entreprendre.service-public.gouv.fr/vosdroits/F31620) : compte d'activité, contrat et rémunération.

Sources consultées le 6 octobre 2026. Les taux de démonstration 45 % / 22 % / 2,85 % sont **illustratifs**, pas des taux légaux universels ni les données d'un salarié. Pour une prévision fiable, obtenir le compte d'activité et le détail de calcul de l'employeur. Pour un rapprochement exact, utiliser `bulletin`.

## Développement et vérification

```sh
uv sync --frozen
uv run ruff check .
uv run ruff format --check .
uv run mypy
uv run pytest
uv export --frozen --no-emit-project --format requirements-txt -o /tmp/portage-requirements.txt
uv run pip-audit --disable-pip --no-deps -r /tmp/portage-requirements.txt
uv build
```

La version Python de développement est fixée dans `.python-version`, les dépendances de développement dans `uv.lock`. Aucune dépendance d'exécution. Tests de propriétés, limites PAS, conservation du budget, objectif minimal, entrées invalides et parcours CLI. CI sur runners GitHub éphémères, jeton en lecture seule.

Codes de sortie : 0 succès, 1 bulletin différent du net attendu, 2 saisie invalide/objectif inaccessible. Pas de télémétrie, serveur, compte utilisateur, appel réseau ou stockage automatique des résultats. Les profils et résultats contiennent potentiellement des données financières : les conserver localement.

Voir [SECURITY.md](SECURITY.md), [registre de vérification](docs/READINESS.md) et [CHANGELOG](CHANGELOG.md). Pour revenir à une version précédente : réinstaller un tag Git (`uv tool install --force git+https://github.com/DeharengOlivier/simulateur-salaire-portage-france.git@v0.1.0`). Aucun profil utilisateur n'est modifié par une mise à jour ou un retour arrière.

Licence MIT.
