# Public dataset verification

Three UCI benchmarks were downloaded and tested against the running API and background worker. Each was trained before and after feature engineering, with five Optuna validation trials per model (20 per run). Automatic champions use validation scores; the figures below are held-out test results.

| Dataset | Rows | Use case | Feature engineering | Champion | Baseline test | Engineered test |
| --- | ---: | --- | --- | --- | ---: | ---: |
| [iris](https://archive.ics.uci.edu/dataset/53/iris) | 150 | classification | sepal_length: Discretize Binning | Random Forest | weighted F1 0.9666 | weighted F1 0.9666 |
| [banknote](https://archive.ics.uci.edu/dataset/267/banknote%2Bauthentication) | 1372 | classification | entropy: Discretize Binning | Neural Network | weighted F1 1.0000 | weighted F1 1.0000 |
| [auto-mpg](https://archive.ics.uci.edu/dataset/9/auto%2Bmpg) | 398 | regression | horsepower: Standard Scaling | Neural Network | MSE 5.3377 | MSE 5.3377 |

The chosen transformations did not improve held-out scores in these runs. This is a before/after comparison, not a claim that every transformation improves accuracy. Five trials per model is a bounded search, not exhaustive optimization.

## What passed

For each dataset: task detection, EDA distributions and correlations, four imputation exports, feature transformation and transformed CSV, baseline and engineered optimized training, all four executable model downloads, raw-input predictions, row SHAP explanations, baseline/shifted drift, and champion switching.

Auto MPG includes six missing horsepower values. Its ID column car_name was omitted, ? was converted to missing numeric values, and origin codes were mapped to USA/Europe/Japan. Iris and Banknote were converted from headerless source files to CSV without changing their observed values.

The profiles and trained projects remain in the app under UCI Iris - Species, UCI Banknote - Authenticity, and UCI Auto MPG - Fuel Economy. An earlier Iris test project is also retained; use the latest matching project.

## Files and rerun

- CSVs, original archives, exported pipelines and machine-readable results: tmp/public-datasets/
- Rerun: python scripts/verify_public_datasets.py
- The script uploads only the public benchmarks through the seeded local demo account and retains the projects for review.

## Attribution

Iris: R. A. Fisher (1936), DOI 10.24432/C56C76. Banknote Authentication: Volker Lohweg (2012), DOI 10.24432/C55P57. Auto MPG: R. Quinlan (1993), DOI 10.24432/C5859H. All three are supplied by UCI under CC BY 4.0: https://creativecommons.org/licenses/by/4.0/. Dataset links above identify the official source pages.

## Fixes found

- All four model families now receive validation-based HPO instead of Random Forest alone.
- Neural networks use internal scaling and support permutation SHAP row explanations.
- Selected training imputation applies to unmodified recommended features; explicit per-feature overrides take precedence.
- KNN feature names remain aligned when an all-empty column is retained.
- Global multiclass SHAP importance averages across classes, and local drivers explain the predicted class.

- Dashboard now shows all projects; the previous five-project cap hid later benchmark uploads.
