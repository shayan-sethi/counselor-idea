import argparse
import os
import joblib
import pandas as pd
import numpy as np

def main():
    parser = argparse.ArgumentParser(
        description="PRISM AI: Course Outcome Prediction Tool (Salary, Continuation, Employment)"
    )
    # Inputs
    parser.add_argument("--subject", type=str, default="CAH17", help="CAH Level subject code prefix (e.g., CAH17, CAH10, CAH02)")
    parser.add_argument("--aim", type=str, default="BSc", help="Degree Aim code/label (e.g., BA, BSc, MEng, FDA)")
    parser.add_argument("--country", type=str, default="England", help="Country of university (England, Scotland, Wales, Northern Ireland)")
    parser.add_argument("--tariff", type=float, default=120.0, help="Average entry tariff score (UCAS points)")
    parser.add_argument("--tef", type=str, default="Gold", choices=["Gold", "Silver", "Bronze", "None"], help="Overall TEF rating")
    parser.add_argument("--tef_exp", type=str, default="Gold", choices=["Gold", "Silver", "Bronze", "None"], help="TEF Student Experience rating")
    parser.add_argument("--tef_out", type=str, default="Gold", choices=["Gold", "Silver", "Bronze", "None"], help="TEF Student Outcomes rating")
    parser.add_argument("--nss", type=float, default=85.0, help="Average student satisfaction score (NSS %)")
    parser.add_argument("--foundation", type=int, choices=[0, 1], default=0, help="Is foundation year included? (0 = No, 1 = Yes)")
    parser.add_argument("--honours", type=int, choices=[0, 1], default=1, help="Is it an Honours degree? (0 = No, 1 = Yes)")
    parser.add_argument("--sandwich", type=int, choices=[0, 1], default=0, help="Is it a sandwich course? (0 = No, 1 = Yes)")
    parser.add_argument("--yearabroad", type=int, choices=[0, 1], default=0, help="Is year abroad included? (0 = No, 1 = Yes)")
    parser.add_argument("--level", type=int, default=4, help="KIS Course Level (e.g. 4 for undergraduate, 5 for postgrad etc.)")

    args = parser.parse_args()

    # TEF Mappings
    tef_map = {"Gold": 3, "Silver": 2, "Bronze": 1, "None": 0}
    tef_overall = tef_map.get(args.tef, 0)
    tef_exp = tef_map.get(args.tef_exp, 0)
    tef_out = tef_map.get(args.tef_out, 0)

    # Format the single row for inference
    input_data = pd.DataFrame([{
        'COUNTRY': args.country,
        'sbj_group': args.subject,
        'KISAIMLABEL': args.aim,
        'FOUNDATION': args.foundation,
        'HONOURS': args.honours,
        'SANDWICH': args.sandwich,
        'YEARABROAD': args.yearabroad,
        'KISLEVEL': args.level,
        'tef_overall': tef_overall,
        'tef_experience': tef_exp,
        'tef_outcomes': tef_out,
        'TARAGG': args.tariff,
        'nss_average_satisfaction': args.nss
    }])

    print("====================================================")
    print("PRISM AI - COURSE PREDICTION TOOL")
    print("====================================================")
    print("Input Profile:")
    print(f"  Subject Group: {args.subject} | Aim: {args.aim} | Country: {args.country}")
    print(f"  Entry Tariff: {args.tariff} UCAS pts | NSS Avg Satisfaction: {args.nss}%")
    print(f"  TEF Overall: {args.tef} | Exp: {args.tef_exp} | Out: {args.tef_out}")
    print(f"  Flags: Foundation={args.foundation}, Honours={args.honours}, Sandwich={args.sandwich}, YearAbroad={args.yearabroad}")
    print("====================================================")

    models_dir = "/Users/ShayanSethi/Documents/GitHub/agent/models"
    targets = ['salary', 'continuation', 'employment']

    for target in targets:
        model_path = os.path.join(models_dir, f"{target}_model.joblib")
        if not os.path.exists(model_path):
            print(f"⚠️ Model '{target}' not found at: {model_path}. Train models first.")
            continue

        try:
            model = joblib.load(model_path)
            prediction = model.predict(input_data)[0]
            
            if target == 'salary':
                print(f"🔮 Predicted Graduate Median Salary: £{prediction:,.2f}")
            elif target == 'continuation':
                print(f"🔮 Predicted Continuation Rate: {prediction:.2f}%")
            elif target == 'employment':
                print(f"🔮 Predicted Professional Employment/Study Rate: {prediction:.2f}%")
        except Exception as e:
            print(f"❌ Error making prediction for {target}: {e}")
            
    print("====================================================")

if __name__ == "__main__":
    main()
