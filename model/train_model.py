import os
import json
import datetime
import sklearn
import numpy as np
import pandas as pd
import joblib

from sklearn.model_selection import train_test_split
from sklearn.tree import DecisionTreeClassifier
from sklearn.metrics import accuracy_score, classification_report, confusion_matrix

np.random.seed(42)

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA_PATH = os.path.join(BASE_DIR, "data", "loan_dataset.csv")
MODEL_PATH = os.path.join(BASE_DIR, "model", "loan_model.pkl")

APPROVAL_THRESHOLD = 6  
NOISE_STD = 1.5         


def rule_based_points(row):
    points = 0

    # Credit score
    if row["credit_score"] >= 750:
        points += 3
    elif row["credit_score"] >= 650:
        points += 2
    elif row["credit_score"] >= 550:
        points += 1
    else:
        points -= 2

    # Debt-to-income (dti)
    if row["dti"] < 0.2:
        points += 2
    elif row["dti"] < 0.4:
        points += 1
    elif row["dti"] < 0.6:
        points += 0
    else:
        points -= 2

    # Loan-to-income ratio
    if row["loan_income_ratio"] < 2:
        points += 2
    elif row["loan_income_ratio"] < 4:
        points += 1
    elif row["loan_income_ratio"] < 6:
        points += 0
    else:
        points -= 2

    # Savings-to-loan ratio
    if row["savings_loan_ratio"] > 1:
        points += 2
    elif row["savings_loan_ratio"] > 0.5:
        points += 1
    elif row["savings_loan_ratio"] > 0.2:
        points += 0
    else:
        points -= 1

    # Previous defaults
    if row["previous_defaults"] == 0:
        points += 2
    elif row["previous_defaults"] == 1:
        points -= 1
    else:
        points -= 3

    # Employment years
    if row["employment_years"] >= 10:
        points += 1
    elif row["employment_years"] >= 5:
        points += 0
    else:
        points -= 1

    # Dependents
    if row["dependents"] <= 1:
        points += 0
    elif row["dependents"] >= 4:
        points -= 1

    # EMI burden vs monthly income
    if row["emi_to_income"] < 0.3:
        points += 1
    elif row["emi_to_income"] < 0.5:
        points += 0
    else:
        points -= 2

    # Assets vs requested loan amount
    if row["assets"] > row["loan_amount"]:
        points += 1

    return points


def main():

    # 1. Load data
    
    df = pd.read_csv(DATA_PATH)
    print("Shape:", df.shape)
    print("Missing values per column:\n", df.isnull().sum())

  
    # 2. Feature engineering

    df["dti"] = df["existing_loan_amount"] / df["annual_income"]
    df["loan_income_ratio"] = df["loan_amount"] / df["annual_income"]
    df["savings_loan_ratio"] = df["savings"] / df["loan_amount"]
    df["emi_to_income"] = df["monthly_emi"] / (df["annual_income"] / 12)  # label-only helper

    
    # 3. Rule-based target with noise (avoids an overconfident, 100%-deterministic label)
  
    df["approval_points"] = df.apply(rule_based_points, axis=1)
    noise = np.random.normal(0, NOISE_STD, len(df))
    df["loan_status"] = ((df["approval_points"] + noise) >= APPROVAL_THRESHOLD).astype(int)
    print("\nTarget distribution:\n", df["loan_status"].value_counts(normalize=True))


    # 4. Select the 16 model features (fixed order)
    
    feature_cols = [
        "age", "annual_income", "credit_score", "loan_amount", "loan_term",
        "existing_loans", "existing_loan_amount", "monthly_emi", "dependents",
        "savings", "employment_years", "previous_defaults", "assets",
        "dti", "loan_income_ratio", "savings_loan_ratio",
    ]
    X = df[feature_cols]
    y = df["loan_status"]

    # 5. Train/test split
    
    X_train, X_test, y_train, y_test = train_test_split(
        X, y, test_size=0.2, random_state=42, stratify=y
    )
    print("\nTrain size:", X_train.shape, " Test size:", X_test.shape)

    # 6. Train the Decision Tree
    
    model = DecisionTreeClassifier(max_depth=6, min_samples_leaf=30, random_state=42)
    model.fit(X_train, y_train)


    # 7. Evaluate
    
    y_pred = model.predict(X_test)
    print("\nAccuracy:", accuracy_score(y_test, y_pred))
    print("\nClassification Report:\n", classification_report(y_test, y_pred))
    print("Confusion Matrix:\n", confusion_matrix(y_test, y_pred))

    importances = pd.Series(model.feature_importances_, index=feature_cols)
    print("\nFeature importances:\n", importances.sort_values(ascending=False))

    # 8. Sanity check — confidence spread (catches the "fixed probability" bug)
  
    test_probs = model.predict_proba(X_test)[:, 1]
    print("\nDistinct probability values on test set:", len(np.unique(test_probs)))
    print("Min probability:", test_probs.min(), " Max probability:", test_probs.max())

    leaf_values = model.tree_.value
    pure_leaves = sum(
        1 for i in range(model.tree_.node_count)
        if model.tree_.children_left[i] == -1 and leaf_values[i][0].min() == 0
    )
    print(f"Pure (100%-confidence) leaves: {pure_leaves} / {model.get_n_leaves()}")

 
    # 8b. Save REAL evaluation metrics so the API / Model Insights page never invents numbers
    report = classification_report(y_test, y_pred, output_dict=True)
    metrics = {
        "accuracy": float(accuracy_score(y_test, y_pred)),
        "per_class": {
            "rejected": {k: float(report["0"][k]) for k in ("precision", "recall", "f1-score", "support")},
            "approved": {k: float(report["1"][k]) for k in ("precision", "recall", "f1-score", "support")},
        },
        "confusion_matrix": confusion_matrix(y_test, y_pred).tolist(),  # rows=actual [0,1], cols=predicted [0,1]
        "train_size": int(len(X_train)),
        "test_size": int(len(X_test)),
        "trained_at": datetime.datetime.now(datetime.timezone.utc).isoformat(),
        "sklearn_version": sklearn.__version__,
        "label_note": "Labels are synthetic (rule-based points + Gaussian noise), so accuracy measures "
                      "how well the tree recovers that rule, not real-world lending outcomes.",
        "training_ranges": {c: [float(df[c].min()), float(df[c].max())] for c in feature_cols[:13]},
    }
    with open(os.path.join(BASE_DIR, "model", "metrics.json"), "w", encoding="utf-8") as fh:
        json.dump(metrics, fh, indent=2)
    print("Saved metrics -> model/metrics.json")

    # 9. Save the trained model
  
    joblib.dump(model, MODEL_PATH)
    loaded_model = joblib.load(MODEL_PATH)
    print("\nSaved model ->", MODEL_PATH)
    print("Feature order:", list(loaded_model.feature_names_in_))


if __name__ == "__main__":
    main()
