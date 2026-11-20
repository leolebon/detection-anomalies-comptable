"""
EXERCICE — Étape 3b : les règles d'audit.

Chaque règle prend le tableau `ecritures` (une ligne par écriture, produit
par anomalies.ecritures.resumer_ecritures) et renvoie une Series de booléens,
de même index : True = l'écriture déclenche une alerte.

Une règle doit tenir en 1 à 5 lignes de pandas, sans boucle `for`.

Ta mission : remplacer chaque `raise NotImplementedError` par ton code.
Vérifie ton travail avec :   pytest tests/test_rules.py -v
"""

from __future__ import annotations

import pandas as pd


def regle_weekend(ecritures: pd.DataFrame) -> pd.Series:
    """Écriture datée d'un samedi ou d'un dimanche. """
    return ecritures["EcritureDate"].dt.day_of_week > 4 #5 et 6 sont samedi et dimanche


def regle_montant_rond(ecritures: pd.DataFrame, multiple: int = 1000) -> pd.Series:
    """Montant au moins égal à `multiple` ET multiple exact de `multiple`
    (5 000,00 ou 12 000,00 par exemple).
    Indice : l'opérateur % (modulo)."""
    m_abs = ecritures["montant"].abs()
    return (m_abs >= multiple)&(m_abs % multiple == 0)


def regle_sous_seuil(ecritures: pd.DataFrame, seuil: float = 10_000, marge: float = 0.05) -> pd.Series:
    """Montant dans la zone [seuil × (1 - marge) ; seuil[, c'est-à-dire
    juste sous le seuil d'approbation. Avec les valeurs par défaut :
    de 9 500 inclus à 10 000 exclu."""
    return ecritures["montant"].between(left=seuil*(1-marge), right=seuil, inclusive="left")


def regle_doublons(ecritures: pd.DataFrame) -> pd.Series:
    """Même JournalCode, même tiers, même montant ET même PieceRef qu'une
    autre écriture. On ne marque PAS la première occurrence (l'originale,
    chronologiquement : tri par EcritureDate puis EcritureNum), seulement
    les suivantes."""
    tri = ecritures.sort_values(by=["EcritureDate","EcritureNum"])
    doublons = tri.duplicated(subset=["JournalCode","tiers","montant","PieceRef"], keep="first")
    return doublons.reindex(ecritures.index)


def regle_auto_validation(ecritures: pd.DataFrame) -> pd.Series:
    """La personne qui a saisi l'écriture est aussi celle qui l'a validée
    (non-respect de la séparation des tâches)."""
    return ecritures["Utilisateur"] == ecritures["Validateur"]


def regle_fin_exercice(ecritures: pd.DataFrame, jours: int = 3) -> pd.Series:
    """Écriture du journal des opérations diverses ("OD"), passée dans les
    `jours` derniers jours de l'année (29, 30 ou 31 décembre par défaut),
    qui mouvemente un compte de produit (numéro commençant par "7").
    C'est le schéma classique pour gonfler le chiffre d'affaires à la clôture."""
    nb_jours_annee = 365 + ecritures["EcritureDate"].dt.is_leap_year #365 + 1 ou + 0 (bisextile ou non)
    return ((ecritures["comptes"].str.contains(r"\b7"))&(ecritures["JournalCode"]=="OD")&(ecritures["EcritureDate"].dt.day_of_year > (nb_jours_annee - jours)))

# ---------------------------------------------------------------------------
# FOURNI : applique toutes les règles d'un coup (rien à coder ici)
# ---------------------------------------------------------------------------

REGLES = {
    "weekend": regle_weekend,
    "montant_rond": regle_montant_rond,
    "sous_seuil": regle_sous_seuil,
    "doublon": regle_doublons,
    "auto_validation": regle_auto_validation,
    "fin_exercice": regle_fin_exercice,
}


def appliquer_regles(ecritures: pd.DataFrame) -> pd.DataFrame:
    """Une colonne booléenne par règle + `nb_alertes`, le nombre de règles déclenchées."""
    alertes = pd.DataFrame({nom: regle(ecritures) for nom, regle in REGLES.items()})
    alertes.insert(0, "EcritureNum", ecritures["EcritureNum"])
    alertes["nb_alertes"] = alertes[list(REGLES)].sum(axis=1)
    return alertes
