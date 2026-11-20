"""
EXERCICE — Étape 3a : la loi de Benford.

Dans beaucoup de données financières « naturelles », le premier chiffre
n'est PAS réparti uniformément : il vaut 1 dans environ 30 % des cas,
et 9 dans moins de 5 % des cas. C'est la loi de Benford :

    P(premier chiffre = d) = log10(1 + 1/d)      pour d = 1, ..., 9

Quand quelqu'un invente des montants, il a tendance à s'en écarter.
Les auditeurs utilisent donc ce test pour repérer des populations suspectes.

Ta mission : remplacer chaque `raise NotImplementedError` par ton code.
Vérifie ton travail avec :   pytest tests/test_benford.py -v
"""

from __future__ import annotations

import numpy as np
import pandas as pd
from scipy import stats

#%%
def premier_chiffre(montants: pd.Series) -> pd.Series:
    """Renvoie le premier chiffre significatif (entier de 1 à 9) de chaque montant.
    Les montants nuls ou négatifs sont ignorés (ils disparaissent du résultat).
    Exemples : 123.4 -> 1 ;  0.056 -> 5 ;  45000 -> 4 ;  9 -> 9"""
    pos = montants[montants > 0]
    pwr = np.floor(np.log10(pos))
    chiffre = (pos / 10**pwr)
    return chiffre.astype(int)

#%%

def frequences_benford() -> pd.Series:
    """Les 9 probabilités théoriques de Benford.
    Renvoie une Series d'index 1..9 dont les valeurs somment à 1."""
    
    chiffres = np.arange(1, 10)
    return pd.Series(np.log10(1 + 1/chiffres), index=chiffres)

# Seuils de Nigrini (référence en audit) pour le premier chiffre, appliqués au MAD
SEUILS_MAD = [
    (0.006, "conformité forte"),
    (0.012, "conformité acceptable"),
    (0.015, "conformité limite"),
]

#%%

def analyse_benford(montants: pd.Series) -> dict:
    """Compare la distribution des premiers chiffres à la loi de Benford.

    Renvoie un dictionnaire avec :
      "observees" : Series 1..9, proportion observée de chaque premier chiffre
      "attendues" : Series 1..9, proportions de Benford
      "chi2"      : statistique du test du khi-deux
      "p_value"   : p-value du test du khi-deux
      "mad"       : écart absolu moyen entre proportions observées et attendues
      "conclusion": le libellé de SEUILS_MAD correspondant au MAD,
                    ou "non conforme" s'il dépasse 0.015"""
                    
    chiffres = premier_chiffre(montants)
    n = len(chiffres)
    obs = chiffres.value_counts(normalize=True).reindex(range(1,10), fill_value = 0)
    att = frequences_benford()
    stat, pv = stats.chisquare(f_obs = obs*n, f_exp = att*n) # *n transforme les proportions en nombre d'écritures
    mad = (obs - att).abs().mean()
    
    if mad < SEUILS_MAD[0][0]:
        ccl = SEUILS_MAD[0][1]
    elif(mad < SEUILS_MAD[1][0]):
        ccl = SEUILS_MAD[1][1]
    elif(mad < SEUILS_MAD[2][0]):
        ccl = SEUILS_MAD[2][1]
    else:
        ccl = "non conforme"
                
    analyse = {
        "observees" : obs,
        "attendues" : att,
        "chi2"      : stat,
        "p_value"   : pv,
        "mad"       : mad,
        "conclusion": ccl
            }
    return analyse
