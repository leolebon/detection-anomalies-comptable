# Journal Entry Anomaly Detection

**Flagging the journal entries an auditor should review first, in a French general ledger (FEC).**

Auditors cannot review hundreds of thousands of ledger lines by hand. This project builds a tool that reads a general ledger in the French *Fichier des Écritures Comptables* (FEC) format, runs classic audit tests and machine learning models, and ranks entries by risk — with a plain-language reason for every alert. The auditor stays in charge: the tool prioritises and explains, it does not decide.

> **Status: work in progress.** Exploration and Benford analysis are done; audit rules are being implemented. See the [roadmap](#roadmap).

## Key findings so far

Analysis of one synthetic year of activity: **42,467 journal entries (110,004 ledger lines)**, all balanced (total debits = total credits).

- **Segregation of duties breaches.** 35 entries were entered *and* approved by the same accountant. A further 35 entries were entered by the two managers — whose role is to approve, not to post — each approving the other's entries. This is a textbook *management override of controls* pattern (ISA 240).
- **Year-end manual entries.** The miscellaneous journal (OD) holds one payroll entry per month, then jumps to 36 entries in December, on the last days of the year.
- **Benford's law: why the chi-square test is not enough.** First digits are in close conformity with Benford's law (MAD = 0.0020), yet the chi-square test rejects it (p = 0.00008). With 42,000 entries the chi-square test flags even negligible deviations, which is why auditors rely on the MAD. Global conformity also does not rule out fraud: a few hundred anomalies are diluted in the population.
- **Know what a row is.** Sales and purchases have the most *lines* (3 per entry), but the bank journal has the most *entries* (17,385), since it records both customer receipts and supplier payments.

## Approach

| Step | Content | Status |
| --- | --- | --- |
| 1. Synthetic data | One year of a fictional SME in FEC format, with 210 hidden anomalies of 6 types | Done |
| 2. Exploration | Volumes, seasonality, amount distribution, who enters vs. who approves | Done |
| 3a. Benford's law | First-digit test: chi-square and mean absolute deviation (Nigrini thresholds) | Done |
| 3b. Audit rules | Weekend postings, round amounts, amounts just below the approval threshold, duplicate invoices, self-approval, year-end revenue entries | In progress |
| 4. Machine learning | Unsupervised models (Isolation Forest, Local Outlier Factor, autoencoder), evaluated with precision@50 and recall@500 | To do |
| 5. Explainability & app | SHAP explanations and a Streamlit app that exports the ranked list to Excel | To do |

## Quick start

```bash
python -m venv .venv
.venv\Scripts\activate           # macOS/Linux: source .venv/bin/activate
pip install -r requirements.txt

python -m anomalies.generate     # creates data/fec.csv and data/verite_terrain.csv
pytest                           # runs the test suite
```

Requires Python 3.10 to 3.12.

## Project structure

```
anomalies/
  generate.py      synthetic FEC generator with hidden anomalies
  ecritures.py     loads the FEC and aggregates lines into entries
  benford.py       Benford's law test
  rules.py         audit rules
notebooks/
  01_exploration.ipynb   exploratory analysis of the ledger
tests/             automated tests (pytest)
```

## Data

All data is **synthetic**: no real company data is used. The generator injects known anomalies and keeps a separate answer key (`verite_terrain.csv`), used only to *evaluate* the detectors, never to train them. The `Utilisateur` (entered by) and `Validateur` (approved by) columns are not part of the FEC standard; they mimic the audit trail of accounting software.

## Tech stack

Python, pandas, NumPy, SciPy, scikit-learn, pytest, Jupyter — Streamlit and SHAP to come.

## Acknowledgements

The synthetic data generator and test scaffolding were set up with the help of an AI assistant. The exploration, the audit tests and their analysis are my own work.

---

### En français

Outil de détection d'écritures comptables suspectes dans un FEC : tests d'audit classiques (loi de Benford, séparation des tâches, doublons…) puis modèles de machine learning non supervisés, avec une explication pour chaque alerte. Données entièrement synthétiques. Le code et les carnets sont commentés en français.
