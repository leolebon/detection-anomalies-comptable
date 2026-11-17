# Détection d'écritures comptables suspectes

> Projet en cours. Ce README sera réécrit à la fin (étape 6 du guide).

Outil qui analyse un grand livre au format FEC (Fichier des Écritures Comptables)
et classe les écritures qu'un auditeur devrait vérifier en priorité, avec la
raison de chaque alerte.

## Démarrage rapide

```bash
python -m venv .venv
source .venv/bin/activate        # Windows : .venv\Scripts\activate
pip install -r requirements.txt

python -m anomalies.generate     # crée data/fec.csv et data/verite_terrain.csv
pytest                           # lance les tests
```

## Organisation

| Fichier | Rôle | État |
| --- | --- | --- |
| `anomalies/generate.py` | Génère un FEC synthétique avec des fraudes cachées | Fourni |
| `anomalies/ecritures.py` | Charge le FEC, regroupe les lignes par écriture | Fourni |
| `anomalies/benford.py` | Test de la loi de Benford | À coder |
| `anomalies/rules.py` | Règles d'audit (week-end, montants ronds, doublons…) | À coder |
| `notebooks/01_exploration.ipynb` | Exploration guidée des données | À faire |
| `tests/` | Tests automatiques : ils passent au vert quand ton code est juste | Fourni |

## Données

Toutes les données sont **synthétiques**. Aucune donnée réelle d'entreprise
n'est utilisée. Les colonnes `Utilisateur` et `Validateur` ne font pas partie
de la norme FEC ; elles imitent le journal d'audit d'un logiciel comptable.
