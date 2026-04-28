import sqlite3
import pandas as pd
import ast
from sklearn.model_selection import train_test_split
from sklearn.linear_model import LogisticRegression
from sklearn.ensemble import RandomForestClassifier
from sklearn.metrics import accuracy_score, classification_report
import joblib

# Load DB
conn = sqlite3.connect("projyA.db")
df = pd.read_sql_query("SELECT * FROM history", conn)

# Convert string → list
df["matched_skills"] = df["matched_skills"].apply(ast.literal_eval)
df["missing_skills"] = df["missing_skills"].apply(ast.literal_eval)

# Feature engineering
df["matched_count"] = df["matched_skills"].apply(len)
df["missing_count"] = df["missing_skills"].apply(len)

# Features
X = df[["semantic_score", "skill_score", "matched_count", "missing_count"]]

# Target
y = df["similarity"].apply(lambda x: 1 if x > 0.6 else 0)

print("\nClass Distribution:")
print(y.value_counts())

# Split
X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=0.2, random_state=42)

# ===== MODEL 1: Logistic Regression =====
lr = LogisticRegression()
lr.fit(X_train, y_train)

y_pred_lr = lr.predict(X_test)

# ===== MODEL 2: Random Forest =====
rf = RandomForestClassifier()
rf.fit(X_train, y_train)

y_pred_rf = rf.predict(X_test)

# ===== EVALUATION =====

print("---- Logistic Regression ----")
print("Accuracy:", accuracy_score(y_test, y_pred_lr))
print(classification_report(y_test, y_pred_lr))

print("\n---- Random Forest ----")
print("Accuracy:", accuracy_score(y_test, y_pred_rf))
print(classification_report(y_test, y_pred_rf))

# Save best model
acc_lr = accuracy_score(y_test, y_pred_lr)
acc_rf = accuracy_score(y_test, y_pred_rf)

print("\nModel Comparison:")
print(f"LR Accuracy: {acc_lr}")
print(f"RF Accuracy: {acc_rf}")

if acc_rf > acc_lr:
    joblib.dump(rf, "model.pkl")
    print("\n✅ Random Forest saved as best model")
else:
    joblib.dump(lr, "model.pkl")
    print("\n✅ Logistic Regression saved as best model")

print("\n✅ Best model saved successfully")