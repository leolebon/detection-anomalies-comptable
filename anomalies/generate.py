"""
Générateur de grand livre comptable synthétique, au format FEC.

Le FEC (Fichier des Écritures Comptables) est le format que toute entreprise
française doit pouvoir remettre à l'administration fiscale. Un auditeur
travaille très souvent à partir de ce fichier.

Ce script fabrique une année d'activité d'une PME fictive :
  - des factures de vente et d'achat,
  - leurs règlements (encaissements et paiements),
  - les salaires de chaque mois,
puis y cache volontairement quelques écritures frauduleuses ou anormales.

Usage (depuis la racine du projet) :
    python -m anomalies.generate
    python -m anomalies.generate --n-factures 50000 --seed 7

Fichiers produits :
    data/fec.csv              le grand livre : une ligne = un mouvement au débit OU au crédit
    data/verite_terrain.csv   la liste des écritures falsifiées et leur type.
                              À n'utiliser QUE pour évaluer tes détecteurs, jamais pour détecter !
"""

from __future__ import annotations

import argparse
from pathlib import Path

import numpy as np
import pandas as pd

# ---------------------------------------------------------------------------
# Paramètres de l'entreprise fictive
# ---------------------------------------------------------------------------

ANNEE = 2025
SEUIL_APPROBATION = 10_000  # au-delà de ce montant, un responsable doit valider
TAUX_TVA = 0.20
TAUX_ANOMALIES = 0.005  # 0,5 % des écritures sont falsifiées

COMPTES = {
    "401000": "Fournisseurs",
    "411000": "Clients",
    "421000": "Personnel - rémunérations dues",
    "445660": "TVA déductible sur ABS",
    "445710": "TVA collectée",
    "512000": "Banque",
    "607000": "Achats de marchandises",
    "613200": "Locations immobilières",
    "622600": "Honoraires",
    "641000": "Rémunérations du personnel",
    "706000": "Prestations de services",
}

JOURNAUX = {"VE": "Ventes", "AC": "Achats", "BQ": "Banque", "OD": "Opérations diverses"}

COMPTABLES = ["amartin", "bdurand", "cpetit", "dleroy", "emoreau"]  # saisissent
RESPONSABLES = ["fsimon", "glaurent"]  # valident

TYPES_ANOMALIES = [
    "weekend",          # écriture passée un samedi ou un dimanche
    "montant_rond",     # facture fournisseur d'un montant parfaitement rond
    "sous_seuil",       # montant juste sous le seuil d'approbation (fractionnement)
    "doublon",          # même facture fournisseur saisie deux fois
    "auto_validation",  # la même personne saisit et valide
    "fin_exercice",     # chiffre d'affaires fictif passé en OD le 30 ou 31 décembre
]

COLONNES_FEC = [
    "JournalCode", "JournalLib", "EcritureNum", "EcritureDate", "CompteNum",
    "CompteLib", "CompAuxNum", "CompAuxLib", "PieceRef", "PieceDate",
    "EcritureLib", "Debit", "Credit", "EcritureLet", "DateLet", "ValidDate",
    "Montantdevise", "Idevise",
]
# Deux colonnes en plus, qui ne font PAS partie de la norme FEC mais existent
# dans les logiciels comptables (journal d'audit) : qui a saisi, qui a validé.
COLONNES_EXTRA = ["Utilisateur", "Validateur"]


# ---------------------------------------------------------------------------
# Outils
# ---------------------------------------------------------------------------

def jours_ouvres(annee: int) -> np.ndarray:
    """Tous les jours du lundi au vendredi de l'année (jours fériés ignorés)."""
    jours = np.arange(f"{annee}-01-01", f"{annee + 1}-01-01", dtype="datetime64[D]")
    return jours[np.is_busday(jours)]


def poids_saisonniers(jours: np.ndarray) -> np.ndarray:
    """Plus d'activité en fin d'année, moins en août : une PME réaliste."""
    mois = jours.astype("datetime64[M]").astype(int) % 12 + 1
    facteur = {1: 0.9, 2: 0.9, 3: 1.0, 4: 1.0, 5: 1.0, 6: 1.1,
               7: 0.8, 8: 0.5, 9: 1.1, 10: 1.1, 11: 1.2, 12: 1.3}
    p = np.array([facteur[m] for m in mois], dtype=float)
    return p / p.sum()


def montant_naturel(rng: np.random.Generator, mediane: float = 1200, dispersion: float = 1.3) -> float:
    """Montant TTC tiré d'une loi log-normale : beaucoup de petites factures,
    quelques grosses. Ce type de distribution respecte la loi de Benford."""
    return round(float(rng.lognormal(np.log(mediane), dispersion)), 2)


def decaler_jours_ouvres(date: np.datetime64, n: int) -> np.datetime64:
    return np.busday_offset(date, n, roll="forward")


# ---------------------------------------------------------------------------
# 1. Les opérations normales
# ---------------------------------------------------------------------------

def generer_operations(n_factures: int, rng: np.random.Generator) -> list[dict]:
    """Crée la liste des opérations (une opération = une future écriture)."""
    jours = jours_ouvres(ANNEE)
    p = poids_saisonniers(jours)
    fin_annee = np.datetime64(f"{ANNEE}-12-31")

    clients = [f"C{i:04d}" for i in range(1, 201)]
    fournisseurs = [f"F{i:03d}" for i in range(1, 81)]
    comptes_charges = ["607000", "613200", "622600"]

    operations: list[dict] = []
    compteur_piece = 0

    for _ in range(n_factures):
        compteur_piece += 1
        date = rng.choice(jours, p=p)
        ttc = montant_naturel(rng)
        if rng.random() < 0.5:
            op = {"type": "vente", "journal": "VE", "tiers": rng.choice(clients),
                  "piece": f"FV{compteur_piece:06d}"}
        else:
            op = {"type": "achat", "journal": "AC", "tiers": rng.choice(fournisseurs),
                  "piece": f"FA{compteur_piece:06d}", "charge": rng.choice(comptes_charges)}
        op.update(date=date, ttc=ttc)
        operations.append(op)

        # 85 % des factures sont réglées dans l'année, 15 à 60 jours ouvrés plus tard
        if rng.random() < 0.85:
            date_reglement = decaler_jours_ouvres(date, int(rng.integers(15, 60)))
            if date_reglement <= fin_annee:
                compteur_piece += 1
                operations.append({
                    "type": "encaissement" if op["type"] == "vente" else "paiement",
                    "journal": "BQ", "tiers": op["tiers"], "date": date_reglement,
                    "ttc": ttc, "piece": f"RB{compteur_piece:06d}",
                })

    # Salaires : le dernier jour ouvré de chaque mois, puis leur paiement
    masse_salariale = 38_000.0
    for mois in range(1, 13):
        fin_mois = np.datetime64(f"{ANNEE}-{mois:02d}") + np.timedelta64(1, "M")
        dernier_jour = np.busday_offset(fin_mois.astype("datetime64[D]"), -1, roll="backward")
        montant = round(masse_salariale * rng.uniform(0.97, 1.05), 2)
        compteur_piece += 2
        operations.append({"type": "salaires", "journal": "OD", "tiers": None,
                           "date": dernier_jour, "ttc": montant, "piece": f"SA{mois:02d}{ANNEE}"})
        paiement = min(decaler_jours_ouvres(dernier_jour, 1), fin_annee)
        operations.append({"type": "paiement_salaires", "journal": "BQ", "tiers": None,
                           "date": paiement, "ttc": montant, "piece": f"VS{mois:02d}{ANNEE}"})

    # Qui saisit, qui valide (toujours deux personnes différentes)
    for op in operations:
        op["utilisateur"] = rng.choice(COMPTABLES)
        op["validateur"] = rng.choice(RESPONSABLES)
        op["anomalie"] = None
    return operations


# ---------------------------------------------------------------------------
# 2. Les anomalies cachées
# ---------------------------------------------------------------------------

def injecter_anomalies(operations: list[dict], rng: np.random.Generator) -> list[dict]:
    """Modifie ou ajoute quelques opérations frauduleuses, réparties
    à parts égales entre les types d'anomalies."""
    n_par_type = max(1, int(len(operations) * TAUX_ANOMALIES / len(TYPES_ANOMALIES)))
    achats = [op for op in operations if op["type"] == "achat" and op["anomalie"] is None]
    factures = [op for op in operations if op["type"] in ("vente", "achat")]
    rng.shuffle(achats)
    rng.shuffle(factures)
    nouvelles: list[dict] = []

    def prendre(liste: list[dict]) -> dict:
        while True:
            op = liste.pop()
            if op["anomalie"] is None:
                return op

    for _ in range(n_par_type):
        # Écriture passée un week-end
        op = prendre(factures)
        jour = op["date"]
        samedi = np.busday_offset(jour, 0, roll="forward", weekmask="Sat")
        if samedi > np.datetime64(f"{ANNEE}-12-27"):  # ne pas déborder sur l'année suivante
            samedi = np.busday_offset(jour, 0, roll="backward", weekmask="Sat")
        op["date"] = samedi + np.timedelta64(int(rng.integers(0, 2)), "D")
        op["anomalie"] = "weekend"

        # Facture fournisseur au montant parfaitement rond
        op = prendre(achats)
        op["ttc"] = float(rng.choice([5_000, 8_000, 10_000, 12_000, 15_000, 20_000, 25_000]))
        op["anomalie"] = "montant_rond"

        # Montant juste sous le seuil pour éviter la validation d'un responsable
        op = prendre(achats)
        op["ttc"] = round(float(rng.uniform(SEUIL_APPROBATION * 0.95, SEUIL_APPROBATION - 0.01)), 2)
        op["anomalie"] = "sous_seuil"

        # Même facture fournisseur saisie une deuxième fois quelques jours après
        originale = prendre(achats)
        copie = dict(originale)
        copie["date"] = min(decaler_jours_ouvres(originale["date"], int(rng.integers(2, 20))),
                            np.datetime64(f"{ANNEE}-12-31"))
        copie["utilisateur"] = rng.choice(COMPTABLES)
        copie["anomalie"] = "doublon"
        nouvelles.append(copie)

        # La personne qui saisit valide elle-même son écriture
        op = prendre(achats)
        op["ttc"] = montant_naturel(rng, mediane=14_000, dispersion=0.4)
        op["validateur"] = op["utilisateur"]
        op["anomalie"] = "auto_validation"

        # Chiffre d'affaires fictif pour embellir les comptes de l'année
        saisi_par, valide_par = rng.permutation(RESPONSABLES)[:2]
        nouvelles.append({
            "type": "ca_fictif", "journal": "OD", "tiers": f"C{int(rng.integers(1, 201)):04d}",
            "date": np.datetime64(f"{ANNEE}-12-{int(rng.integers(30, 32))}"),
            "ttc": round(float(rng.uniform(20_000, 90_000)), 2),
            "piece": f"REG{int(rng.integers(1000, 9999))}",
            "utilisateur": saisi_par, "validateur": valide_par,
            "anomalie": "fin_exercice",
        })

    return operations + nouvelles


# ---------------------------------------------------------------------------
# 3. Transformer les opérations en lignes FEC (partie double)
# ---------------------------------------------------------------------------

def lignes_comptables(op: dict) -> list[tuple[str, str | None, str, float, float]]:
    """Renvoie les mouvements (compte, compte auxiliaire, libellé, débit, crédit)
    d'une opération. Le total des débits est toujours égal au total des crédits."""
    ttc = op["ttc"]
    ht = round(ttc / (1 + TAUX_TVA), 2)
    tva = round(ttc - ht, 2)
    t = op["tiers"]
    match op["type"]:
        case "vente":
            lib = f"Facture client {t}"
            return [("411000", t, lib, ttc, 0.0), ("706000", None, lib, 0.0, ht),
                    ("445710", None, lib, 0.0, tva)]
        case "achat":
            lib = f"Facture fournisseur {t}"
            return [(op["charge"], None, lib, ht, 0.0), ("445660", None, lib, tva, 0.0),
                    ("401000", t, lib, 0.0, ttc)]
        case "encaissement":
            lib = f"Règlement client {t}"
            return [("512000", None, lib, ttc, 0.0), ("411000", t, lib, 0.0, ttc)]
        case "paiement":
            lib = f"Paiement fournisseur {t}"
            return [("401000", t, lib, ttc, 0.0), ("512000", None, lib, 0.0, ttc)]
        case "salaires":
            lib = "Salaires du mois"
            return [("641000", None, lib, ttc, 0.0), ("421000", None, lib, 0.0, ttc)]
        case "paiement_salaires":
            lib = "Virement des salaires"
            return [("421000", None, lib, ttc, 0.0), ("512000", None, lib, 0.0, ttc)]
        case "ca_fictif":
            lib = "Régularisation chiffre d'affaires"
            return [("411000", t, lib, ttc, 0.0), ("706000", None, lib, 0.0, ht),
                    ("445710", None, lib, 0.0, tva)]
    raise ValueError(f"Type d'opération inconnu : {op['type']}")


def construire_fec(operations: list[dict], rng: np.random.Generator) -> tuple[pd.DataFrame, pd.DataFrame]:
    # Tri chronologique puis numérotation : impossible de repérer une fraude à son numéro
    operations = sorted(operations, key=lambda op: (op["date"], op["journal"]))
    compteurs = {j: 0 for j in JOURNAUX}
    lignes, verite = [], []

    for op in operations:
        compteurs[op["journal"]] += 1
        num = f"{op['journal']}{compteurs[op['journal']]:06d}"
        date = op["date"]
        valid = decaler_jours_ouvres(date, int(rng.integers(0, 4)))
        valid = min(valid, np.datetime64(f"{ANNEE + 1}-01-15"))
        for compte, aux, lib, debit, credit in lignes_comptables(op):
            lignes.append({
                "JournalCode": op["journal"], "JournalLib": JOURNAUX[op["journal"]],
                "EcritureNum": num, "EcritureDate": str(date).replace("-", ""),
                "CompteNum": compte, "CompteLib": COMPTES[compte],
                "CompAuxNum": aux or "", "CompAuxLib": aux or "",
                "PieceRef": op["piece"], "PieceDate": str(date).replace("-", ""),
                "EcritureLib": lib, "Debit": debit, "Credit": credit,
                "EcritureLet": "", "DateLet": "", "ValidDate": str(valid).replace("-", ""),
                "Montantdevise": "", "Idevise": "",
                "Utilisateur": op["utilisateur"], "Validateur": op["validateur"],
            })
        if op["anomalie"]:
            verite.append({"EcritureNum": num, "type_anomalie": op["anomalie"]})

    fec = pd.DataFrame(lignes, columns=COLONNES_FEC + COLONNES_EXTRA)
    return fec, pd.DataFrame(verite, columns=["EcritureNum", "type_anomalie"])


# ---------------------------------------------------------------------------
# Point d'entrée
# ---------------------------------------------------------------------------

def generer(n_factures: int = 25_000, seed: int = 42) -> tuple[pd.DataFrame, pd.DataFrame]:
    """Génère le FEC et la vérité terrain, sans rien écrire sur le disque."""
    rng = np.random.default_rng(seed)
    operations = generer_operations(n_factures, rng)
    operations = injecter_anomalies(operations, rng)
    return construire_fec(operations, rng)


def main() -> None:
    parser = argparse.ArgumentParser(description="Génère un FEC synthétique avec anomalies cachées.")
    parser.add_argument("--n-factures", type=int, default=25_000, help="nombre de factures (défaut : 25 000)")
    parser.add_argument("--seed", type=int, default=42, help="graine aléatoire, pour des résultats reproductibles")
    parser.add_argument("--sortie", type=Path, default=Path("data"), help="dossier de sortie")
    args = parser.parse_args()

    fec, verite = generer(args.n_factures, args.seed)
    args.sortie.mkdir(parents=True, exist_ok=True)
    fec.to_csv(args.sortie / "fec.csv", index=False)
    verite.to_csv(args.sortie / "verite_terrain.csv", index=False)

    print(f"{fec['EcritureNum'].nunique():,} écritures, {len(fec):,} lignes -> {args.sortie / 'fec.csv'}")
    print(f"{len(verite)} anomalies cachées -> {args.sortie / 'verite_terrain.csv'}")
    print(verite["type_anomalie"].value_counts().to_string())


if __name__ == "__main__":
    main()
