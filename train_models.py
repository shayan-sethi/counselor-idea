import pandas as pd
import numpy as np
import os
import json
import joblib
from sklearn.model_selection import train_test_split
from sklearn.compose import ColumnTransformer
from sklearn.pipeline import Pipeline
from sklearn.impute import SimpleImputer
from sklearn.preprocessing import OneHotEncoder
from sklearn.ensemble import RandomForestRegressor
from sklearn.metrics import r2_score, mean_absolute_error, mean_squared_error

def train_and_evaluate():
    dataset_path = "/Users/ShayanSethi/Documents/GitHub/agent/data/cleaned_courses_dataset.csv"
    models_dir = "/Users/ShayanSethi/Documents/GitHub/agent/models"
    os.makedirs(models_dir, exist_ok=True)

    if not os.path.exists(dataset_path):
        print(f"❌ Dataset not found at: {dataset_path}. Please run clean_data.py first.")
        return

    print("Loading cleaned dataset...")
    df = pd.read_csv(dataset_path)

    # Define features
    categorical_features = ['COUNTRY', 'sbj_group', 'KISAIMLABEL']
    numeric_features = [
        'FOUNDATION', 'HONOURS', 'SANDWICH', 'YEARABROAD', 
        'KISLEVEL', 'tef_overall', 'tef_experience', 'tef_outcomes',
        'TARAGG', 'nss_average_satisfaction'
    ]
    all_features = categorical_features + numeric_features

    # Impute categorical missing values to prevent issues in ColumnTransformer
    for col in categorical_features:
        df[col] = df[col].astype(str).replace('nan', np.nan).fillna('Unknown')

    targets = {
        'salary': {
            'column': 'GOINSTMED',
            'label': 'Graduate Median Salary (£)',
            'description': 'Predicting median salary 3 years post-graduation'
        },
        'continuation': {
            'column': 'UCONT',
            'label': 'Student Continuation Rate (%)',
            'description': 'Predicting percentage of students continuing after year 1'
        },
        'employment': {
            'column': 'WORKSTUDY',
            'label': 'Professional Employment/Study Rate (%)',
            'description': 'Predicting percentage of graduates entering professional work/study'
        }
    }

    metrics_summary = {}
    report_content = "# AI Model Training & Evaluation Report\n\n"
    report_content += "This report summarizes the performance of the three predictive AI models trained on the cleaned Discover Uni (KIS) higher education dataset.\n\n"

    for target_name, info in targets.items():
        print(f"\n--- Training Model for {info['label']} ({target_name}) ---")
        col = info['column']
        
        # Filter rows with non-null targets
        target_df = df[df[col].notnull()].copy()
        
        if len(target_df) < 100:
            print(f"⚠️ Too few samples ({len(target_df)}) to train {target_name} model. Skipping.")
            continue

        print(f"Number of samples: {len(target_df)}")

        X = target_df[all_features]
        y = target_df[col]

        # Train/Test Split
        X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=0.2, random_state=42)

        # Preprocessing Pipelines
        numeric_transformer = Pipeline(steps=[
            ('imputer', SimpleImputer(strategy='median'))
        ])

        categorical_transformer = Pipeline(steps=[
            ('onehot', OneHotEncoder(handle_unknown='ignore'))
        ])

        preprocessor = ColumnTransformer(
            transformers=[
                ('num', numeric_transformer, numeric_features),
                ('cat', categorical_transformer, categorical_features)
            ]
        )

        # Full Model Pipeline
        model_pipeline = Pipeline(steps=[
            ('preprocessor', preprocessor),
            ('regressor', RandomForestRegressor(n_estimators=100, random_state=42, n_jobs=-1))
        ])

        # Train model
        print("Fitting model...")
        model_pipeline.fit(X_train, y_train)

        # Predict and evaluate
        y_pred = model_pipeline.predict(X_test)
        r2 = r2_score(y_test, y_pred)
        mae = mean_absolute_error(y_test, y_pred)
        rmse = np.sqrt(mean_squared_error(y_test, y_pred))

        print(f"Performance on Test Set:")
        print(f"  R² Score: {r2:.4f}")
        print(f"  MAE: {mae:.2f}")
        print(f"  RMSE: {rmse:.2f}")

        # Save model
        model_path = os.path.join(models_dir, f"{target_name}_model.joblib")
        joblib.dump(model_pipeline, model_path)
        print(f"✔ Saved model to {model_path}")

        # Extract feature importances
        # Get onehot encoder features
        onehot_cols = (model_pipeline.named_steps['preprocessor']
                       .named_transformers_['cat']
                       .named_steps['onehot']
                       .get_feature_names_out(categorical_features))
        
        feature_names = list(numeric_features) + list(onehot_cols)
        importances = model_pipeline.named_steps['regressor'].feature_importances_
        
        # Create sorted dataframe of importances
        imp_df = pd.DataFrame({'feature': feature_names, 'importance': importances})
        imp_df = imp_df.sort_values(by='importance', ascending=False).head(10)

        # Save metrics
        metrics_summary[target_name] = {
            'r2': float(r2),
            'mae': float(mae),
            'rmse': float(rmse),
            'samples': len(target_df),
            'top_features': imp_df.to_dict(orient='records')
        }

        # Format markdown section
        report_content += f"## Model: {info['label']} ({target_name.capitalize()})\n"
        report_content += f"{info['description']}.\n\n"
        report_content += f"### Performance Metrics\n"
        report_content += f"- **Samples Used**: {len(target_df):,}\n"
        report_content += f"- **R² Score**: {r2:.4f}\n"
        report_content += f"- **Mean Absolute Error (MAE)**: {mae:.2f}\n"
        report_content += f"- **Root Mean Squared Error (RMSE)**: {rmse:.2f}\n\n"
        report_content += f"### Top 10 Feature Importances\n"
        report_content += "| Feature | Importance |\n"
        report_content += "| --- | --- |\n"
        for _, row in imp_df.iterrows():
            report_content += f"| `{row['feature']}` | {row['importance']:.4f} |\n"
        report_content += "\n---\n\n"

    # Save JSON summary metrics
    metrics_path = os.path.join(models_dir, "model_metrics.json")
    with open(metrics_path, "w") as f:
        json.dump(metrics_summary, f, indent=2)
    print(f"✔ Saved summary metrics to {metrics_path}")

    # Save Markdown report
    report_path = os.path.join(models_dir, "training_report.md")
    with open(report_path, "w") as f:
        f.write(report_content)
    print(f"✔ Saved Markdown report to {report_path}")

if __name__ == "__main__":
    train_and_evaluate()
