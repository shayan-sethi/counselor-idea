import pandas as pd
import numpy as np
import os

def clean_and_merge():
    data_dir = "/Users/ShayanSethi/Documents/GitHub/agent/on_2026_07_21_17_38_31"
    output_dir = "/Users/ShayanSethi/Documents/GitHub/agent/data"
    os.makedirs(output_dir, exist_ok=True)

    print("Loading datasets...")
    # Read files
    kiscourse = pd.read_csv(os.path.join(data_dir, "KISCOURSE.csv"), low_memory=False)
    institution = pd.read_csv(os.path.join(data_dir, "INSTITUTION.csv"), low_memory=False)
    continuation = pd.read_csv(os.path.join(data_dir, "CONTINUATION.csv"), low_memory=False)
    gosalary = pd.read_csv(os.path.join(data_dir, "GOSALARY.csv"), low_memory=False)
    employment = pd.read_csv(os.path.join(data_dir, "EMPLOYMENT.csv"), low_memory=False)
    tariff = pd.read_csv(os.path.join(data_dir, "TARIFF.csv"), low_memory=False)
    nss = pd.read_csv(os.path.join(data_dir, "NSS.csv"), low_memory=False)
    tef = pd.read_csv(os.path.join(data_dir, "TEFOutcome.csv"), low_memory=False)
    sbj = pd.read_csv(os.path.join(data_dir, "SBJ.csv"), low_memory=False)
    kisaim = pd.read_csv(os.path.join(data_dir, "KISAIM.csv"), low_memory=False)
    exclusions = pd.read_csv(os.path.join(data_dir, "Exclusions.csv"), low_memory=False)

    # Standardize columns (strip spaces)
    for df in [kiscourse, institution, continuation, gosalary, employment, tariff, nss, tef, sbj, kisaim, exclusions]:
        df.columns = df.columns.str.strip()

    print(f"Initial courses count in KISCOURSE: {len(kiscourse)}")

    # 1. Apply Exclusions
    exclusions['excl_key'] = (
        exclusions['PUBUKPRN'].astype(str).str.strip() + "_" + 
        exclusions['KISCOURSEID'].astype(str).str.strip() + "_" + 
        exclusions['KISMODE'].astype(str).str.strip()
    )
    kiscourse['excl_key'] = (
        kiscourse['PUBUKPRN'].astype(str).str.strip() + "_" + 
        kiscourse['KISCOURSEID'].astype(str).str.strip() + "_" + 
        kiscourse['KISMODE'].astype(str).str.strip()
    )
    
    excluded_keys = set(exclusions['excl_key'].dropna())
    kiscourse = kiscourse[~kiscourse['excl_key'].isin(excluded_keys)].copy()
    kiscourse.drop(columns=['excl_key'], inplace=True)
    print(f"Courses count after exclusions: {len(kiscourse)}")

    # 2. Clean numeric targets/features and aggregate duplicates per course
    keys = ['PUBUKPRN', 'KISCOURSEID', 'KISMODE']

    # Continuation
    continuation['UCONT'] = pd.to_numeric(continuation['UCONT'], errors='coerce')
    continuation_agg = continuation.groupby(keys, as_index=False)['UCONT'].mean()

    # Salary
    gosalary['GOINSTMED'] = pd.to_numeric(gosalary['GOINSTMED'], errors='coerce')
    gosalary['GOINSTLQ'] = pd.to_numeric(gosalary['GOINSTLQ'], errors='coerce')
    gosalary['GOINSTUQ'] = pd.to_numeric(gosalary['GOINSTUQ'], errors='coerce')
    gosalary_agg = gosalary.groupby(keys, as_index=False)[['GOINSTMED', 'GOINSTLQ', 'GOINSTUQ']].mean()

    # Employment
    employment['WORKSTUDY'] = pd.to_numeric(employment['WORKSTUDY'], errors='coerce')
    employment_agg = employment.groupby(keys, as_index=False)['WORKSTUDY'].mean()

    # Tariff
    tariff['TARAGG'] = pd.to_numeric(tariff['TARAGG'], errors='coerce')
    tariff_agg = tariff.groupby(keys, as_index=False)['TARAGG'].mean()

    # NSS Questions Q1 to Q28
    q_cols = [f'Q{i}' for i in range(1, 29)]
    q_cols = [q for q in q_cols if q in nss.columns]
    for q in q_cols:
        nss[q] = pd.to_numeric(nss[q], errors='coerce')
    # Calculate average NSS satisfaction per row
    nss['nss_average_satisfaction'] = nss[q_cols].mean(axis=1)
    
    # Aggregate NSS per course
    nss_agg = nss.groupby(keys, as_index=False)[['nss_average_satisfaction'] + q_cols].mean()

    # 3. Clean categorical values
    # TEF Outcome
    tef_mapped = tef.copy()
    tef_map = {"Gold": 3, "Silver": 2, "Bronze": 1}
    tef_mapped['tef_overall'] = tef_mapped['OVERALL_RATING'].str.strip().map(tef_map).fillna(0)
    tef_mapped['tef_experience'] = tef_mapped['STUDENT_EXPERIENCE_RATING'].str.strip().map(tef_map).fillna(0)
    tef_mapped['tef_outcomes'] = tef_mapped['STUDENT_OUTCOMES_RATING'].str.strip().map(tef_map).fillna(0)
    tef_clean = tef_mapped[['PUBUKPRN', 'tef_overall', 'tef_experience', 'tef_outcomes']].drop_duplicates('PUBUKPRN')

    # Subject code (extract first 5 chars e.g. CAH01)
    sbj_clean = sbj.copy()
    sbj_clean['sbj_group'] = sbj_clean['SBJ'].astype(str).str.strip().str[:5]
    sbj_clean = sbj_clean.drop_duplicates(subset=keys)

    # Institution
    inst_clean = institution[['PUBUKPRN', 'LEGAL_NAME', 'COUNTRY']].drop_duplicates('PUBUKPRN')

    # KIS Aim
    kisaim_clean = kisaim[['KISAIMCODE', 'KISAIMLABEL']].drop_duplicates('KISAIMCODE')

    # Course general binary flags
    for col in ['FOUNDATION', 'HONOURS', 'SANDWICH', 'YEARABROAD']:
        kiscourse[col] = pd.to_numeric(kiscourse[col], errors='coerce').fillna(0).astype(int)

    # 4. Merge sequentially
    merged = kiscourse.merge(
        inst_clean, on='PUBUKPRN', how='left'
    ).merge(
        continuation_agg, on=keys, how='left'
    ).merge(
        gosalary_agg, on=keys, how='left'
    ).merge(
        employment_agg, on=keys, how='left'
    ).merge(
        tariff_agg, on=keys, how='left'
    ).merge(
        nss_agg, on=keys, how='left'
    ).merge(
        tef_clean, on='PUBUKPRN', how='left'
    ).merge(
        sbj_clean[keys + ['sbj_group']], on=keys, how='left'
    ).merge(
        kisaim_clean, on='KISAIMCODE', how='left'
    )

    # Fill missing quality ratings with 0
    merged['tef_overall'] = merged['tef_overall'].fillna(0)
    merged['tef_experience'] = merged['tef_experience'].fillna(0)
    merged['tef_outcomes'] = merged['tef_outcomes'].fillna(0)

    # Final cleanup & save
    output_path = os.path.join(output_dir, "cleaned_courses_dataset.csv")
    merged.to_csv(output_path, index=False)
    print(f"✔ Cleaned and merged dataset successfully created at: {output_path}")
    print(f"Columns: {list(merged.columns)}")
    print(f"Row count: {len(merged)}")
    
    # Print target coverage summary
    print("\nTarget Coverage Summary:")
    print(f"  GOINSTMED (Salary) non-null: {merged['GOINSTMED'].notnull().sum()}")
    print(f"  UCONT (Continuation) non-null: {merged['UCONT'].notnull().sum()}")
    print(f"  WORKSTUDY (Employment) non-null: {merged['WORKSTUDY'].notnull().sum()}")

if __name__ == "__main__":
    clean_and_merge()
