"""Tests de l'exercice sur les règles d'audit. Lance-les avec :  pytest tests/test_rules.py -v

Les premiers tests utilisent un petit tableau fait à la main : tu peux
vérifier chaque résultat de tête. Le dernier test lance tes règles sur un
vrai grand livre généré et vérifie qu'elles retrouvent les fraudes cachées.
"""

import pandas as pd
import pytest

from anomalies.ecritures import resumer_ecritures
from anomalies.generate import generer
from anomalies.rules import (
    appliquer_regles,
    regle_auto_validation,
    regle_doublons,
    regle_fin_exercice,
    regle_montant_rond,
    regle_sous_seuil,
    regle_weekend,
)


@pytest.fixture
def ecritures():
    """Six écritures fabriquées à la main (une ligne = une écriture)."""
    return pd.DataFrame({
        "EcritureNum": ["AC1", "AC2", "AC3", "BQ1", "OD1", "OD2"],
        "JournalCode": ["AC", "AC", "AC", "BQ", "OD", "OD"],
        "EcritureDate": pd.to_datetime(
            ["2025-03-14", "2025-03-15", "2025-03-20", "2025-03-16", "2025-12-31", "2025-12-31"]),
        #                 vendredi      samedi        jeudi         dimanche      mercredi      mercredi
        "PieceRef": ["FA1", "FA2", "FA1", "RB1", "REG1", "SA12"],
        "Utilisateur": ["amartin", "bdurand", "cpetit", "amartin", "fsimon", "dleroy"],
        "Validateur": ["fsimon", "glaurent", "fsimon", "amartin", "glaurent", "fsimon"],
        "montant": [1_234.56, 9_800.00, 1_234.56, 12_000.00, 45_000.00, 39_000.12],
        "tiers": ["F001", "F002", "F001", "F001", "C0001", ""],
        "comptes": ["401000 445660 607000", "401000 445660 622600", "401000 445660 607000",
                    "401000 512000", "411000 445710 706000", "421000 641000"],
    })


def test_weekend(ecritures):
    assert regle_weekend(ecritures).tolist() == [False, True, False, True, False, False]


def test_montant_rond(ecritures):
    assert regle_montant_rond(ecritures).tolist() == [False, False, False, True, True, False]


def test_montant_rond_ignore_les_petits_montants():
    petits = pd.DataFrame({"montant": [0.0, 500.0, 1_000.0]})
    assert regle_montant_rond(petits).tolist() == [False, False, True]


def test_sous_seuil(ecritures):
    assert regle_sous_seuil(ecritures).tolist() == [False, True, False, False, False, False]


def test_sous_seuil_bornes():
    bornes = pd.DataFrame({"montant": [9_499.99, 9_500.00, 9_999.99, 10_000.00]})
    assert regle_sous_seuil(bornes).tolist() == [False, True, True, False]


def test_doublons_marque_seulement_la_copie(ecritures):
    assert regle_doublons(ecritures).tolist() == [False, False, True, False, False, False]


def test_doublons_garde_l_ordre_d_origine(ecritures):
    melange = ecritures.iloc[[2, 0, 1, 3, 4, 5]]  # la copie arrive en premier dans le tableau
    resultat = regle_doublons(melange)
    assert resultat.index.tolist() == melange.index.tolist()
    assert resultat.tolist() == [True, False, False, False, False, False]


def test_auto_validation(ecritures):
    assert regle_auto_validation(ecritures).tolist() == [False, False, False, True, False, False]


def test_fin_exercice(ecritures):
    # OD2 est en OD le 31/12 mais ne touche pas de compte 7 : pas d'alerte
    assert regle_fin_exercice(ecritures).tolist() == [False, False, False, False, True, False]


def test_appliquer_regles(ecritures):
    alertes = appliquer_regles(ecritures)
    assert alertes["nb_alertes"].tolist() == [0, 2, 1, 3, 2, 0]


def test_les_regles_retrouvent_toutes_les_fraudes_cachees():
    """Le vrai test : sur un grand livre généré, chaque règle doit retrouver
    100 % des anomalies de son type (rappel = 1)."""
    from anomalies.ecritures import charger_fec  # noqa: F401  (pour te montrer d'où vient le FEC)

    fec, verite = generer(n_factures=6_000, seed=123)
    for col in ["EcritureDate", "PieceDate", "ValidDate"]:
        fec[col] = pd.to_datetime(fec[col], format="%Y%m%d")
    ecritures = resumer_ecritures(fec)
    alertes = appliquer_regles(ecritures).set_index("EcritureNum")

    for type_anomalie, groupe in verite.groupby("type_anomalie"):
        detectees = alertes.loc[groupe["EcritureNum"], type_anomalie]
        rappel = detectees.mean()
        assert rappel == 1.0, f"La règle '{type_anomalie}' ne retrouve que {rappel:.0%} de ses anomalies"
