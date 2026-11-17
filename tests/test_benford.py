"""Tests de l'exercice Benford. Lance-les avec :  pytest tests/test_benford.py -v"""

import numpy as np
import pandas as pd
import pytest

from anomalies.benford import analyse_benford, frequences_benford, premier_chiffre


def test_premier_chiffre_exemples():
    montants = pd.Series([123.4, 0.056, 45_000.0, 9.0, 1_000.0, 2.5])
    assert premier_chiffre(montants).tolist() == [1, 5, 4, 9, 1, 2]


def test_premier_chiffre_ignore_zero_et_negatifs():
    montants = pd.Series([0.0, -350.0, 72.0])
    assert premier_chiffre(montants).tolist() == [7]


def test_frequences_benford():
    f = frequences_benford()
    assert list(f.index) == list(range(1, 10))
    assert f.sum() == pytest.approx(1.0)
    assert f[1] == pytest.approx(0.30103, abs=1e-4)
    assert f[9] == pytest.approx(0.04576, abs=1e-4)
    assert f.is_monotonic_decreasing


def test_analyse_cles_du_resultat():
    rng = np.random.default_rng(0)
    res = analyse_benford(pd.Series(rng.lognormal(7, 2.5, 5_000)))
    assert set(res) >= {"observees", "attendues", "chi2", "p_value", "mad", "conclusion"}
    assert res["observees"].sum() == pytest.approx(1.0)
    assert 0 <= res["p_value"] <= 1


def test_analyse_donnees_naturelles_conformes():
    # Une log-normale très dispersée suit Benford de très près
    rng = np.random.default_rng(1)
    res = analyse_benford(pd.Series(rng.lognormal(7, 2.5, 20_000)))
    assert res["mad"] < 0.006
    assert res["conclusion"] == "conformité forte"


def test_analyse_montants_inventes_non_conformes():
    # Des montants « inventés » uniformément entre 100 et 999 ne suivent pas Benford
    rng = np.random.default_rng(2)
    res = analyse_benford(pd.Series(rng.uniform(100, 999, 20_000)))
    assert res["mad"] > 0.015
    assert res["conclusion"] == "non conforme"
    assert res["p_value"] < 0.001
