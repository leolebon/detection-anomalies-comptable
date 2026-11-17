"""
Outils pour charger le FEC et passer de « une ligne par mouvement »
à « une ligne par écriture ».  Ce module est FOURNI : tu n'as rien à coder ici,
mais lis-le, tu t'en serviras partout.

Une écriture (EcritureNum) regroupe 2 ou 3 lignes du FEC : par exemple une
facture d'achat = une ligne de charge, une ligne de TVA, une ligne fournisseur.
Les tests d'audit raisonnent presque toujours au niveau de l'écriture.
"""

from __future__ import annotations

from pathlib import Path

import pandas as pd


def charger_fec(chemin: str | Path = "data/fec.csv") -> pd.DataFrame:
    """Lit le FEC en gardant les numéros de compte comme du texte
    (sinon "401000" deviendrait le nombre 401000) et convertit les dates."""
    fec = pd.read_csv(
        chemin,
        dtype={"CompteNum": str, "CompAuxNum": str, "EcritureDate": str,
               "PieceDate": str, "ValidDate": str},
        keep_default_na=False,
    )
    for col in ["EcritureDate", "PieceDate", "ValidDate"]:
        fec[col] = pd.to_datetime(fec[col], format="%Y%m%d")
    return fec


def resumer_ecritures(fec: pd.DataFrame) -> pd.DataFrame:
    """Une ligne par écriture, avec les informations utiles aux tests d'audit.

    Colonnes renvoyées :
        EcritureNum, JournalCode, EcritureDate, ValidDate, PieceRef,
        Utilisateur, Validateur,
        montant      : total des débits de l'écriture (= total des crédits)
        tiers        : le compte client ou fournisseur concerné ("" s'il n'y en a pas)
        comptes      : les comptes mouvementés, triés et séparés par des espaces
        nb_lignes    : nombre de lignes de l'écriture
    """
    infos = fec.groupby("EcritureNum", sort=False).agg(
        JournalCode=("JournalCode", "first"),
        EcritureDate=("EcritureDate", "first"),
        ValidDate=("ValidDate", "first"),
        PieceRef=("PieceRef", "first"),
        Utilisateur=("Utilisateur", "first"),
        Validateur=("Validateur", "first"),
        montant=("Debit", "sum"),
        tiers=("CompAuxNum", "max"),  # max() garde la valeur non vide
        comptes=("CompteNum", lambda c: " ".join(sorted(set(c)))),
        nb_lignes=("CompteNum", "size"),
    )
    infos["montant"] = infos["montant"].round(2)
    return infos.reset_index()


def charger_verite(chemin: str | Path = "data/verite_terrain.csv") -> pd.DataFrame:
    """Les anomalies réellement cachées. Pour ÉVALUER uniquement."""
    return pd.read_csv(chemin)
