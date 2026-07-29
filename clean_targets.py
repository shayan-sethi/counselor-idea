import json

mapping = {
    'DU_SRCC': 'Delhi University SRCC',
    'UCLA_PREMED': 'UCLA Pre-Med',
    'IVY_LEAGUE': 'Ivy League',
    'BITS_PILANI': 'BITS Pilani',
    'VIT': 'Vellore Institute of Technology',
    'OXBRIDGE': 'Oxford / Cambridge',
    'STANFORD_CS': 'Stanford Computer Science',
    'AIIMS': 'AIIMS',
    'IIT_BOMBAY': 'IIT Bombay',
    'LSE_ECON': 'LSE Economics',
    'CAMBRIDGE_MED': 'Cambridge Medicine',
    'DU_ST_STEPHENS': 'Delhi University St. Stephens',
    'ASHOKA_UNIV': 'Ashoka University',
    'JEE_MAIN': 'JEE Main Engineering',
    'NEET_UG': 'NEET Medical',
    'CUET_DU_CS': 'Delhi University Computer Science',
    'CUET_DU_ECO': 'Delhi University Economics',
    'CAMBRIDGE_CS': 'Cambridge Computer Science',
    'IMPERIAL_CS': 'Imperial College Computer Science',
    'MIT_STEM': 'MIT STEM',
    'CUSTOM_IMPERIAL_COLLEGE___BSC_COMPUTING': 'Imperial College BSc Computing',
    'CUSTOM_ENGINEERING': 'Engineering',
    'CUSTOM_ENGINEERING_1': 'Engineering 1',
    'CUSTOM_COMPUTER_SCIENCE': 'Computer Science',
    'CUSTOM_MATHEMATICS_AND_COMPUTER_SCIENCE': 'Mathematics and CS',
    'CUSTOM_MATHEMATICS_AND_COMPUTER_SCIENCE__3_OR_4_YEARS_': 'Mathematics and CS (3/4 Yrs)',
    'CUSTOM_COMPUTING': 'Computing',
    'CUSTOM_COMPUTING_1': 'Computing 1',
    'CUSTOM_COMPUTER_GAMES_ART': 'Computer Games Art',
    'CUSTOM_COMPUTER_SCIENCE_1': 'Computer Science 1',
    'CUSTOM_ENGINEERING_2': 'Engineering 2',
    'CUSTOM_UNDERGRADUATE_BACHELORS_PROGRAM': 'Undergraduate Bachelors'
}

def clean_name(t):
    return mapping.get(t, t.replace('_', ' ').title() if '_' in t else t)

# 1. Clean students_db.json
with open("data/students_db.json", "r") as f:
    students = json.load(f)

for s in students:
    if "targets" in s and isinstance(s["targets"], list):
        s["targets"] = [clean_name(t) for t in s["targets"]]

with open("data/students_db.json", "w") as f:
    json.dump(students, f, indent=2)

# 2. Clean requirements_db.json
with open("data/requirements_db.json", "r") as f:
    reqs = json.load(f)

new_reqs = {}
for k, v in reqs.items():
    new_k = clean_name(k)
    v["id"] = new_k
    new_reqs[new_k] = v

with open("data/requirements_db.json", "w") as f:
    json.dump(new_reqs, f, indent=2)

print("Targets cleaned successfully!")
