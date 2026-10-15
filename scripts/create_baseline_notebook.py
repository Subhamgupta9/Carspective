import contextlib
import io
import json
from pathlib import Path

ROOT = Path(r"C:/Projects/smart-used-car-price-prediction")
PATH = ROOT / "notebooks" / "05_baseline_modeling.ipynb"

def markdown(text):
    return {"cell_type": "markdown", "metadata": {}, "source": text.splitlines(keepends=True)}

def code(text):
    return {"cell_type": "code", "execution_count": None, "metadata": {}, "outputs": [], "source": text.splitlines(keepends=True)}

source = '''from pathlib import Path
import platform
import numpy as np
import pandas as pd
import sklearn
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import seaborn as sns
from sklearn.compose import ColumnTransformer, TransformedTargetRegressor
from sklearn.ensemble import RandomForestRegressor, GradientBoostingRegressor
from sklearn.impute import SimpleImputer
from sklearn.linear_model import LinearRegression
from sklearn.metrics import mean_absolute_error, mean_squared_error, r2_score
from sklearn.model_selection import KFold, cross_validate, train_test_split
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import OneHotEncoder, StandardScaler

RANDOM_STATE = 42
PROJECT_ROOT = Path("C:/Projects/smart-used-car-price-prediction")
DATA_PATH = PROJECT_ROOT / "data" / "processed" / "indian_used_cars_features.csv"
OUTPUT_DIR = PROJECT_ROOT / "data" / "processed"
if not DATA_PATH.is_file():
    raise FileNotFoundError(f"Feature dataset not found: {DATA_PATH}")
df = pd.read_csv(DATA_PATH)
assert df.shape == (57480, 13)
assert "price" in df.columns
print(f"Dataset: {DATA_PATH}")
print(f"Shape: {df.shape}; Python: {platform.python_version()}; scikit-learn: {sklearn.__version__}")

target = "price"
numerical_features = ["manufacturing_year", "km_driven", "number_of_owners", "vehicle_age", "log_km_driven"]
categorical_features = ["model", "fuel_type", "transmission_type", "brand", "city", "bodytype", "fuel_transmission_type"]
candidate_features = numerical_features + categorical_features
X, y = df[candidate_features].copy(), df[target].copy()
assert target not in X.columns
X_development, X_test, y_development, y_test = train_test_split(X, y, test_size=0.20, random_state=RANDOM_STATE)
cv = KFold(n_splits=5, shuffle=True, random_state=RANDOM_STATE)
print(f"Development: {len(X_development):,} ({len(X_development)/len(X):.1%}); locked test: {len(X_test):,} ({len(X_test)/len(X):.1%})")
print("Numerical features:", numerical_features)
print("Categorical features:", categorical_features)

def make_one_hot(scale):
    numerical_steps = [("imputer", SimpleImputer(strategy="median"))]
    if scale:
        numerical_steps.append(("scaler", StandardScaler()))
    return ColumnTransformer([
        ("numeric", Pipeline(numerical_steps), numerical_features),
        ("categorical", Pipeline([("imputer", SimpleImputer(strategy="most_frequent")), ("onehot", OneHotEncoder(handle_unknown="ignore"))]), categorical_features),
    ])

def build(model_name, log_target=False):
    if model_name == "Linear Regression":
        prep, estimator = make_one_hot(True), LinearRegression(n_jobs=-1)
    elif model_name == "Random Forest":
        prep, estimator = make_one_hot(False), RandomForestRegressor(n_estimators=30, random_state=RANDOM_STATE, n_jobs=1)
    elif model_name == "Gradient Boosting":
        prep = ColumnTransformer([("numeric", Pipeline([("imputer", SimpleImputer(strategy="median"))]), numerical_features)])
        estimator = GradientBoostingRegressor(random_state=RANDOM_STATE)
    else:
        raise ValueError(model_name)
    if log_target:
        estimator = TransformedTargetRegressor(regressor=estimator, func=np.log1p, inverse_func=np.expm1, check_inverse=False)
    return Pipeline([("preprocess", prep), ("model", estimator)])

experiments = [
    ("BL-01", "Linear Regression", False, "One-hot + median imputation + StandardScaler"),
    ("BL-02", "Linear Regression", True, "One-hot + median imputation + StandardScaler; log1p target"),
    ("BL-03", "Random Forest", False, "One-hot + median imputation; unscaled numeric inputs"),
    ("BL-04", "Gradient Boosting", False, "Numeric-only + median imputation; classic estimator does not accept sparse OHE"),
]
scoring = {"r2": "r2", "mae": "neg_mean_absolute_error", "rmse": "neg_root_mean_squared_error"}
results_rows, predictions_by_id = [], {}
for experiment_id, model_name, log_target, prep_note in experiments:
    pipeline = build(model_name, log_target)
    cv_result = cross_validate(pipeline, X_development, y_development, cv=cv, scoring=scoring, n_jobs=1)
    pipeline.fit(X_development, y_development)
    prediction = pipeline.predict(X_test)
    dimensions = int(pipeline.named_steps["preprocess"].transform(X_development.iloc[:1]).shape[1])
    results_rows.append({
        "Experiment ID": experiment_id, "Model": model_name, "Preprocessing": prep_note, "Target Scale": "log1p(price)" if log_target else "price",
        "CV R² Mean": cv_result["test_r2"].mean(), "CV R² Std": cv_result["test_r2"].std(),
        "CV MAE Mean": -cv_result["test_mae"].mean(), "CV RMSE Mean": -cv_result["test_rmse"].mean(),
        "Test R²": r2_score(y_test, prediction), "Test MAE": mean_absolute_error(y_test, prediction), "Test RMSE": mean_squared_error(y_test, prediction) ** 0.5,
        "Encoded/processed dimensions": dimensions, "Notes": "Baseline evidence only; no tuning or final selection.",
    })
    predictions_by_id[experiment_id] = prediction
    print(f"Completed {experiment_id}: {model_name}, target={'log1p(price)' if log_target else 'price'}")
results = pd.DataFrame(results_rows)
print("\\nModel comparison:\\n", results.to_string(index=False))

ohe_pipeline = build("Linear Regression").fit(X_development, y_development)
encoder = ohe_pipeline.named_steps["preprocess"].named_transformers_["categorical"].named_steps["onehot"]
category_counts = dict(zip(categorical_features, [len(categories) for categories in encoder.categories_]))
print("\\nDevelopment-only OHE categories:", category_counts)
print("One-hot processed dimensionality:", int(ohe_pipeline.named_steps["preprocess"].transform(X_development.iloc[:1]).shape[1]))

test_analysis = X_test.reset_index(drop=True).copy()
test_analysis["actual_price"] = y_test.reset_index(drop=True)
test_analysis["price_segment"] = pd.qcut(test_analysis["actual_price"], q=4, labels=["low", "medium", "high", "very_high"], duplicates="drop")
error_rows, residual_rows = [], []
for experiment_id, prediction in predictions_by_id.items():
    analysis = test_analysis.copy()
    analysis["prediction"] = prediction
    analysis["residual"] = analysis["actual_price"] - analysis["prediction"]
    for segment, subset in analysis.groupby("price_segment", observed=True):
        error_rows.append({"Experiment ID": experiment_id, "Price Segment": str(segment), "Rows": len(subset), "MAE": mean_absolute_error(subset.actual_price, subset.prediction), "RMSE": mean_squared_error(subset.actual_price, subset.prediction) ** 0.5, "Mean Residual": subset.residual.mean()})
    expensive = analysis.actual_price >= analysis.actual_price.quantile(.95)
    oldest = analysis.manufacturing_year <= 2000
    extreme_km = analysis.km_driven >= analysis.km_driven.quantile(.99)
    residual_rows.append({"Experiment ID": experiment_id, "Overall mean residual": analysis.residual.mean(), "Mean residual top 5% price": analysis.loc[expensive, "residual"].mean(), "Mean residual old years<=2000": analysis.loc[oldest, "residual"].mean(), "Mean residual top 1% km": analysis.loc[extreme_km, "residual"].mean()})
error_by_segment = pd.DataFrame(error_rows)
residual_observations = pd.DataFrame(residual_rows)
print("\\nError by actual-test-price segment:\\n", error_by_segment.to_string(index=False))
print("\\nResidual observations (descriptive):\\n", residual_observations.to_string(index=False))

fig, axes = plt.subplots(1, 2, figsize=(15, 5))
for axis, experiment_id in zip(axes, ["BL-02", "BL-03"]):
    analysis = test_analysis.copy()
    analysis["prediction"] = predictions_by_id[experiment_id]
    analysis["residual"] = analysis.actual_price - analysis.prediction
    sns.scatterplot(data=analysis.sample(min(5000, len(analysis)), random_state=RANDOM_STATE), x="prediction", y="residual", alpha=.25, s=12, ax=axis)
    axis.axhline(0, color="black", linewidth=1)
    axis.set(title=f"Locked-test residuals: {experiment_id}", xlabel="Predicted price (₹)", ylabel="Actual - predicted (₹)")
fig.tight_layout()
plt.close(fig)

results.to_csv(OUTPUT_DIR / "baseline_model_results.csv", index=False)
results[["Experiment ID", "Model", "Target Scale", "CV R² Mean", "CV R² Std", "CV MAE Mean", "CV RMSE Mean"]].to_csv(OUTPUT_DIR / "baseline_cv_results.csv", index=False)
error_by_segment.to_csv(OUTPUT_DIR / "baseline_error_by_segment.csv", index=False)
results.to_csv(OUTPUT_DIR / "baseline_model_experiments.csv", index=False)
residual_observations.to_csv(OUTPUT_DIR / "baseline_residual_observations.csv", index=False)
print("\\nReproducibility: random_state=42; split=train_test_split(80/20); CV=KFold(n_splits=5, shuffle=True, random_state=42).")
print("No preprocessing was fit globally; no target encoding or hyperparameter tuning was performed.")
'''

cells = [
    markdown("# Smart Used Car Price Prediction\n\n## Phase 5 — Leakage-Safe Baseline Modeling & Preprocessing Experiment\n\nThe test set is split before preprocessing. Every encoder, imputer, and scaler is fitted only within its pipeline's training data. No production model is selected or saved.\n"),
    markdown("## 1. Load Data and Define Features\n\n`price` is the target; twelve candidate inputs comprise five numeric and seven categorical features. No identifiers or target-derived statistics are included.\n"),
    markdown("## 2. Split and Preprocessing Strategy\n\nA deterministic 80/20 development/test split uses `random_state=42`; model comparison uses 5-fold shuffled KFold on development data only. Linear Regression uses scaled numerical inputs plus OHE. Random Forest uses unscaled numeric inputs plus OHE. Gradient Boosting is a numeric-only baseline because classic sklearn GradientBoostingRegressor cannot accept sparse OHE matrices.\n"),
    markdown("## 3. Experiments\n\nBaselines: Linear Regression on original and log targets, Random Forest on original target, and Gradient Boosting on original target. The log-target pipeline uses `log1p(price)` for fitting and `expm1()` before predictions, so all metrics are in original rupees.\n"),
    code(source),
    markdown("## 4. Residual and Price-Segment Analysis\n\nResidual is actual minus predicted. Test-target quartiles are used only for post-hoc error analysis, never as input features. Observations are not removed based on residuals.\n"),
    markdown("## 5. Baseline Modeling Findings\n\nInterpret all metrics as baseline evidence. CV stability, locked-test results, residual patterns, and sparse OHE dimensionality inform later tuning; they do not establish a final production model.\n"),
]

nb = {"cells": cells, "metadata": {"kernelspec": {"display_name": "Python 3.11 (.venv)", "language": "python", "name": "python3"}, "language_info": {"name": "python", "version": "3.11"}}, "nbformat": 4, "nbformat_minor": 5}
scope = {"__name__": "__main__"}
for number, current in enumerate(cells, 1):
    if current["cell_type"] == "code":
        buffer = io.StringIO()
        with contextlib.redirect_stdout(buffer):
            exec(compile("".join(current["source"]), f"{PATH.name}:cell-{number}", "exec"), scope)
        current["execution_count"] = number
        current["outputs"] = [{"output_type": "stream", "name": "stdout", "text": buffer.getvalue().splitlines(keepends=True)}]
PATH.write_text(json.dumps(nb, indent=1), encoding="utf-8")
print(f"Created and executed: {PATH}")
