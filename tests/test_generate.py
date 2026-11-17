"""Tests du générateur (fourni). Ils doivent passer dès le premier jour :
s'ils échouent, c'est ton installation qu'il faut vérifier."""

import pandas as pd

from anomalies.generate import TYPES_ANOMALIES, generer


def test_le_fec_est_equilibre():
    fec, _ = generer(n_factures=2_000, seed=0)
    totaux = fec.groupby("EcritureNum")[["Debit", "Credit"]].sum().round(2)
    assert (totaux["Debit"] == totaux["Credit"]).all(), "Chaque écriture doit avoir débit = crédit"


def test_toutes_les_dates_sont_dans_l_annee():
    fec, _ = generer(n_factures=2_000, seed=0)
    dates = pd.to_datetime(fec["EcritureDate"], format="%Y%m%d")
    assert dates.dt.year.eq(2025).all()


def test_chaque_type_d_anomalie_est_present():
    _, verite = generer(n_factures=2_000, seed=0)
    assert set(verite["type_anomalie"]) == set(TYPES_ANOMALIES)


def test_reproductible_avec_la_meme_graine():
    fec1, _ = generer(n_factures=500, seed=7)
    fec2, _ = generer(n_factures=500, seed=7)
    pd.testing.assert_frame_equal(fec1, fec2)
