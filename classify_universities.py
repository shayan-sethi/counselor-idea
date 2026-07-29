"""
classify_universities.py
One-time script — run this to build data/university_tiers.json
which maps university name (lowercase) -> tier (1=Elite, 2=Top, 3=Strong, 4=Standard)

Usage:
  .venv/bin/python classify_universities.py
"""
import os, json, time, re
import pandas as pd

# ─── Load Gemini ──────────────────────────────────────
api_key = os.environ.get("GEMINI_API_KEY", "").strip().strip('"')
if not api_key:
    # Try reading from .env
    if os.path.exists(".env"):
        for line in open(".env"):
            if "GEMINI_API_KEY" in line:
                api_key = line.split("=", 1)[1].strip().strip('"').strip("'")

import google.generativeai as genai
genai.configure(api_key=api_key)
model = genai.GenerativeModel("gemini-2.0-flash")

# ─── Load all university names ─────────────────────────
names = set()

# US colleges
us_csv = "data/cleaned_us_colleges.csv"
if os.path.exists(us_csv):
    df = pd.read_csv(us_csv, usecols=["INSTNM"], low_memory=False)
    for n in df["INSTNM"].dropna():
        names.add(str(n).strip())
    print(f"Loaded {len(names)} US colleges")

# UK universities (from courses dataset, get unique LEGAL_NAME)
uk_csv = "data/cleaned_courses_dataset.csv"
if os.path.exists(uk_csv):
    df_uk = pd.read_csv(uk_csv, usecols=["LEGAL_NAME"], low_memory=False).drop_duplicates()
    before = len(names)
    for n in df_uk["LEGAL_NAME"].dropna():
        names.add(str(n).strip())
    print(f"Added {len(names) - before} UK universities")

# Manual colleges_db.json
colleges_db = "data/colleges_db.json"
if os.path.exists(colleges_db):
    for c in json.load(open(colleges_db)):
        names.add(c["name"])

names = sorted(names)
print(f"Total universities to classify: {len(names)}")

# ─── Load existing cache ───────────────────────────────
OUT = "data/university_tiers.json"
cache = {}
if os.path.exists(OUT):
    cache = json.load(open(OUT))
    print(f"Resuming from {len(cache)} cached entries")

remaining = [n for n in names if n.lower() not in cache]
print(f"Need to classify {len(remaining)} universities")

# ─── Classify in batches of 60 ────────────────────────
BATCH = 60
PROMPT_TEMPLATE = """You are an expert on global university prestige.

Classify each university below into exactly one of these tiers:
- Tier 1 (Elite): World's absolute top universities. Near-impossible admission. E.g. Oxford, Cambridge, Imperial, MIT, Harvard, Stanford, Caltech, LSE, ETH Zurich, Princeton, Yale, Columbia, Chicago.
- Tier 2 (Top): Highly selective, excellent reputation. E.g. UCL, Cornell, UCLA, UC Berkeley, Michigan, NYU, Toronto, Melbourne, Edinburgh, Duke, Johns Hopkins, Tufts, Georgetown, Vanderbilt, Emory, King's College London.
- Tier 3 (Strong): Good universities, moderately selective. E.g. Purdue, UMass, Ohio State, Penn State, UT Austin, Wisconsin, Virginia, UNC, Georgia Tech, SUNY, Rutgers, Arizona State.
- Tier 4 (Standard): Open or broad admission, regional universities, community colleges, and lesser-known institutions.

Reply ONLY with a JSON object mapping each university name to its tier number (1, 2, 3, or 4).
Do not include any other text.

Universities to classify:
{names}
"""

def classify_batch(batch):
    name_list = "\n".join(f"- {n}" for n in batch)
    prompt = PROMPT_TEMPLATE.format(names=name_list)
    try:
        resp = model.generate_content(prompt)
        text = resp.text.strip()
        # Strip markdown code fences if any
        text = re.sub(r'^```json\s*', '', text)
        text = re.sub(r'\s*```$', '', text)
        result = json.loads(text)
        return {k.lower(): int(v) for k, v in result.items() if isinstance(v, (int, str))}
    except Exception as e:
        print(f"  ⚠ Batch error: {e}")
        return {}

total_batches = (len(remaining) + BATCH - 1) // BATCH
for i in range(0, len(remaining), BATCH):
    batch = remaining[i:i+BATCH]
    batch_num = i // BATCH + 1
    print(f"  Classifying batch {batch_num}/{total_batches} ({len(batch)} universities)…", end="", flush=True)
    result = classify_batch(batch)
    cache.update(result)
    print(f" got {len(result)} results")

    # Save incrementally in case of interruption
    with open(OUT, "w") as f:
        json.dump(cache, f, indent=2)

    # Respect rate limits
    time.sleep(1.5)

print(f"\n✅ Done! {len(cache)} universities classified → {OUT}")

# Show tier distribution
from collections import Counter
dist = Counter(cache.values())
for t in [1, 2, 3, 4]:
    print(f"  Tier {t}: {dist.get(t, 0)} universities")
