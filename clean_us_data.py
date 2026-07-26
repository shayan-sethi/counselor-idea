import pandas as pd
import os

def clean_us_data():
    base_dir = os.path.dirname(os.path.abspath(__file__))
    input_path = os.path.join(base_dir, "data", "Most-Recent-Cohorts-Institution.csv")
    output_path = os.path.join(base_dir, "data", "cleaned_us_colleges.csv")

    if not os.path.exists(input_path):
        print(f"Error: {input_path} not found.")
        return

    # Load dataset
    print(f"Loading {input_path}...")
    # Use low_memory=False to avoid DtypeWarnings
    df = pd.read_csv(input_path, usecols=['UNITID', 'INSTNM', 'CITY', 'STABBR', 'ADM_RATE', 'INSTURL', 'SAT_AVG'], low_memory=False)

    # Clean missing names
    df = df.dropna(subset=['INSTNM'])

    # Format ADM_RATE as a percentage, fill NaN with a generic string or leave empty
    df['ADM_RATE'] = df['ADM_RATE'].apply(lambda x: f"{float(x)*100:.1f}%" if pd.notna(x) else "N/A")
    
    # Keep SAT_AVG as string or N/A
    df['SAT_AVG'] = df['SAT_AVG'].apply(lambda x: str(int(round(float(x) / 10.0) * 10)) if pd.notna(x) else "N/A")

    # Ensure URLs have http/https
    def clean_url(url):
        if pd.isna(url): return ""
        url = str(url).strip()
        if not url.startswith('http'):
            url = 'https://' + url
        return url

    df['INSTURL'] = df['INSTURL'].apply(clean_url)
    
    import json

    def generate_deadlines(row):
        rate = row['ADM_RATE']
        if pd.isna(rate) or rate == "N/A":
            return json.dumps([{"label": "Rolling Admission", "date": "2027-08-01", "description": "Applications reviewed on a rolling basis."}])
        
        try:
            val = float(rate.replace('%', ''))
        except:
            val = 100
            
        if val < 20.0:
            return json.dumps([
                {"label": "Early Decision", "date": "2026-11-01", "description": "Binding early decision deadline."},
                {"label": "Regular Decision", "date": "2027-01-01", "description": "Standard application deadline."}
            ])
        elif val < 50.0:
            return json.dumps([
                {"label": "Early Action", "date": "2026-11-15", "description": "Non-binding early action."},
                {"label": "Regular Decision", "date": "2027-01-15", "description": "Standard application deadline."}
            ])
        else:
            return json.dumps([
                {"label": "Priority Deadline", "date": "2027-03-01", "description": "Priority for financial aid."},
                {"label": "Rolling Admission", "date": "2027-07-01", "description": "Final rolling admission deadline."}
            ])

    def generate_subject_reqs(row):
        return json.dumps(["4 years English", "3-4 years Mathematics", "3 years Science", "2-3 years Foreign Language"])

    def generate_sat_req(row):
        rate = row['ADM_RATE']
        if pd.isna(rate) or rate == "N/A":
            return "Ignored"
        try:
            val = float(rate.replace('%', ''))
        except:
            val = 100
            
        if val < 10.0:
            return "Required"
        elif val < 70.0:
            return "Optional"
        else:
            return "Ignored"
            
    def generate_required_exams(req):
        if req == "Required":
            return json.dumps(["SAT", "ACT"])
        elif req == "Optional":
            return json.dumps(["SAT (Optional)", "ACT (Optional)"])
        else:
            return json.dumps([])

    df['DEADLINES'] = df.apply(generate_deadlines, axis=1)
    df['SUBJECT_REQUIREMENTS'] = df.apply(generate_subject_reqs, axis=1)
    df['SAT_REQUIREMENT'] = df.apply(generate_sat_req, axis=1)
    df['REQUIRED_EXAMS'] = df['SAT_REQUIREMENT'].apply(generate_required_exams)

    # Save to much smaller CSV
    df.to_csv(output_path, index=False)
    print(f"Successfully saved cleaned US data to {output_path} ({len(df)} records).")

if __name__ == "__main__":
    clean_us_data()
