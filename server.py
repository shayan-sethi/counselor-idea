import os
import json
import datetime
import joblib
import pandas as pd
from flask import Flask, jsonify, request, send_from_directory

# ──────────────────────────────────────────────
#  PRISM Web API Server
# ──────────────────────────────────────────────

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
STUDENTS_PATH = os.path.join(BASE_DIR, "data", "students_db.json")

from prism_agent.knowledge_graph import KnowledgeGraph
from prism_agent.reasoner import Reasoner
from prism_agent.planner import Planner

kg = KnowledgeGraph()
reasoner = Reasoner(kg)
planner = Planner()

# ── Load students ──
def load_students():
    with open(STUDENTS_PATH, "r") as f:
        return json.load(f)

def save_students(students):
    with open(STUDENTS_PATH, "w") as f:
        json.dump(students, f, indent=2)

STUDENTS = load_students()

def next_student_id():
    """Generate next STU_NNN id."""
    nums = []
    for s in STUDENTS:
        try:
            nums.append(int(s["id"].replace("STU_", "")))
        except ValueError:
            pass
    return f"STU_{(max(nums) + 1 if nums else 1):03d}"

# ── Pre-load ML models ──
MODELS_DIR = os.path.join(BASE_DIR, "models")
ML_MODELS = {}
for t in ["salary", "continuation", "employment"]:
    p = os.path.join(MODELS_DIR, f"{t}_model.joblib")
    if os.path.exists(p):
        ML_MODELS[t] = joblib.load(p)

MODEL_METRICS = {}
mp = os.path.join(MODELS_DIR, "model_metrics.json")
if os.path.exists(mp):
    with open(mp, "r") as f:
        MODEL_METRICS = json.load(f)

print("✔ PRISM engine + ML models loaded.")

# ──────────────────────────────────────────────
#  Flask App
# ──────────────────────────────────────────────

app = Flask(__name__, static_folder="static", static_url_path="/static")

# ── Page routes ──

@app.route("/")
def index():
    return send_from_directory("static", "index.html")

@app.route("/student")
def student_portal():
    return send_from_directory("static", "student.html")

# ── Read endpoints ──

@app.route("/api/students")
def api_students():
    return jsonify(STUDENTS)

@app.route("/api/student/<student_id>")
def api_student_single(student_id):
    s = next((s for s in STUDENTS if s["id"] == student_id), None)
    if not s:
        return jsonify({"error": "Not found"}), 404
    return jsonify(s)

@app.route("/api/targets")
def api_targets():
    return jsonify(kg.requirements)

@app.route("/api/targets", methods=["POST"])
def api_create_target():
    data = request.get_json()
    if not data:
        return jsonify({"error": "No data"}), 400

    name = data.get("name", "").strip()
    track = data.get("track", "UK").strip()
    type_ = data.get("type", "UniversityCourse").strip()
    university = data.get("university", "").strip()

    if not name:
        return jsonify({"error": "Target name is required"}), 400

    # Auto-generate a clean uppercase ID
    target_id = data.get("id", "").strip().upper()
    if not target_id:
        clean_name = "".join(c if c.isalnum() else "_" for c in name).upper()
        target_id = f"CUSTOM_{clean_name}"
    
    # Simple deduplication
    original_id = target_id
    counter = 1
    while target_id in kg.requirements:
        target_id = f"{original_id}_{counter}"
        counter += 1

    new_target = {
        "id": target_id,
        "name": name,
        "track": track,
        "type": type_,
        "university": university or None,
        "deadlines": data.get("deadlines", []),
        "subject_prerequisites": data.get("subject_prerequisites", []),
        "admission_tests": data.get("admission_tests", []),
        "grade_prerequisites": data.get("grade_prerequisites", []),
        "portfolio_tier": int(data.get("portfolio_tier", 3)),
        "citations": data.get("citations", [])
    }

    kg.requirements[target_id] = new_target
    with open(kg.db_path, "w") as f:
        json.dump(kg.requirements, f, indent=2)
    
    # Force reasoner to see the newly loaded kg targets
    kg.load_database()

    return jsonify(new_target), 201

@app.route("/api/targets/<target_id>", methods=["DELETE"])
def api_delete_target(target_id):
    if target_id not in kg.requirements:
        return jsonify({"error": "Target not found"}), 404
    
    del kg.requirements[target_id]
    with open(kg.db_path, "w") as f:
        json.dump(kg.requirements, f, indent=2)
    
    kg.load_database()
    return jsonify({"ok": True})

@app.route("/api/model_metrics")
def api_model_metrics():
    return jsonify(MODEL_METRICS)

# ── Create student ──

# ── UK Course Database Search Endpoints ──

@app.route("/api/search_unis")
def api_search_unis():
    query = request.args.get("q", "").strip().lower()
    df_path = os.path.join(BASE_DIR, "data", "cleaned_courses_dataset.csv")
    if not os.path.exists(df_path):
        return jsonify([])
    
    try:
        df = pd.read_csv(df_path, usecols=["LEGAL_NAME"])
        unis = df["LEGAL_NAME"].dropna().unique()
        if query:
            filtered = [u for u in unis if query in u.lower()]
        else:
            filtered = list(unis[:50])
        return jsonify(sorted(filtered))
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route("/api/search_courses")
def api_search_courses():
    uni = request.args.get("uni", "").strip()
    query = request.args.get("q", "").strip().lower()
    df_path = os.path.join(BASE_DIR, "data", "cleaned_courses_dataset.csv")
    if not os.path.exists(df_path):
        return jsonify([])

    try:
        df = pd.read_csv(df_path, usecols=["LEGAL_NAME", "TITLE", "TARAGG", "sbj_group"])
        if uni:
            df = df[df["LEGAL_NAME"].str.lower() == uni.lower()]
        
        if query:
            df = df[df["TITLE"].str.lower().str.contains(query, na=False)]
            
        results = []
        # Group by course title to drop duplicates
        grouped = df.drop_duplicates(subset=["TITLE"])
        for _, row in grouped.head(100).iterrows():
            results.append({
                "title": row["TITLE"],
                "subject_group": row["sbj_group"] if pd.notnull(row["sbj_group"]) else None,
                "tariff": float(row["TARAGG"]) if pd.notnull(row["TARAGG"]) else None
            })
        return jsonify(results)
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route("/api/students", methods=["POST"])
def api_create_student():
    data = request.get_json()
    if not data:
        return jsonify({"error": "No data"}), 400

    name = data.get("name", "").strip()
    board = data.get("board", "CBSE")
    class_level = data.get("class_level", 12)
    board_subjects = data.get("board_subjects", [])
    targets = data.get("targets", [])

    if not name:
        return jsonify({"error": "Name is required"}), 400
    if not board_subjects:
        return jsonify({"error": "At least one board subject required"}), 400

    student = {
        "id": next_student_id(),
        "name": name,
        "class_level": int(class_level),
        "board": board,
        "board_subjects": board_subjects,
        "cuet_subjects": data.get("cuet_subjects", []),
        "grades": data.get("grades", {}),
        "standardized_tests": data.get("standardized_tests", {}),
        "portfolio": data.get("portfolio", []),
        "targets": targets,
        "status": data.get("status", {
            "cuet_form_submitted": False,
            "tmua_registered": False,
            "sat_score": None
        })
    }

    # Add planned_class_11_subjects for class 10 students
    if int(class_level) == 10 and data.get("planned_class_11_subjects"):
        student["planned_class_11_subjects"] = data["planned_class_11_subjects"]

    STUDENTS.append(student)
    save_students(STUDENTS)

    # Run compliance check immediately
    result = reasoner.evaluate_student(student)
    for tid, tres in result["targets"].items():
        if not tres["compliant"]:
            rems = planner.get_remediations(result)
            tres["remediations"] = rems.get(tid, [])
        else:
            tres["remediations"] = []

    return jsonify({"student": student, "audit": result}), 201

# ── Update student ──

@app.route("/api/students/<student_id>", methods=["PUT"])
def api_update_student(student_id):
    data = request.get_json()
    if not data:
        return jsonify({"error": "No data"}), 400

    idx = next((i for i, s in enumerate(STUDENTS) if s["id"] == student_id), None)
    if idx is None:
        return jsonify({"error": "Student not found"}), 404

    student = STUDENTS[idx]

    # Update allowed fields
    for field in ["name", "board", "class_level", "board_subjects", "cuet_subjects",
                  "grades", "standardized_tests", "portfolio", "targets", "status",
                  "planned_class_11_subjects"]:
        if field in data:
            student[field] = data[field]

    if "class_level" in data:
        student["class_level"] = int(data["class_level"])

    STUDENTS[idx] = student
    save_students(STUDENTS)
    return jsonify({"student": student})

# ── Delete student ──

@app.route("/api/students/<student_id>", methods=["DELETE"])
def api_delete_student(student_id):
    global STUDENTS
    before = len(STUDENTS)
    STUDENTS = [s for s in STUDENTS if s["id"] != student_id]
    if len(STUDENTS) == before:
        return jsonify({"error": "Not found"}), 404
    save_students(STUDENTS)
    return jsonify({"ok": True})

# ── Evaluate ──

@app.route("/api/evaluate", methods=["POST"])
def api_evaluate():
    data = request.get_json()
    student_id = data.get("student_id")
    simulated_subjects = data.get("simulated_subjects")

    student = next((s for s in STUDENTS if s["id"] == student_id), None)
    if not student:
        return jsonify({"error": "Student not found"}), 404

    result = reasoner.evaluate_student(student, simulated_subjects=simulated_subjects)
    for tid, tres in result["targets"].items():
        if not tres["compliant"]:
            rems = planner.get_remediations(result)
            tres["remediations"] = rems.get(tid, [])
        else:
            tres["remediations"] = []

    return jsonify(result)

@app.route("/api/evaluate_cohort")
def api_evaluate_cohort():
    results = {}
    for student in STUDENTS:
        result = reasoner.evaluate_student(student)
        for tid, tres in result["targets"].items():
            if not tres["compliant"]:
                rems = planner.get_remediations(result)
                tres["remediations"] = rems.get(tid, [])
            else:
                tres["remediations"] = []
        results[student["id"]] = result
    return jsonify(results)

# ── ML Predict ──

@app.route("/api/predict", methods=["POST"])
def api_predict():
    data = request.get_json()
    tef_map = {"Gold": 3, "Silver": 2, "Bronze": 1, "None": 0}
    input_data = pd.DataFrame([{
        'COUNTRY': data.get('country', 'England'),
        'sbj_group': data.get('subject', 'CAH17'),
        'KISAIMLABEL': data.get('aim', 'BSc'),
        'FOUNDATION': data.get('foundation', 0),
        'HONOURS': data.get('honours', 1),
        'SANDWICH': data.get('sandwich', 0),
        'YEARABROAD': data.get('yearabroad', 0),
        'KISLEVEL': data.get('level', 4),
        'tef_overall': tef_map.get(data.get('tef', 'Gold'), 0),
        'tef_experience': tef_map.get(data.get('tef_exp', 'Gold'), 0),
        'tef_outcomes': tef_map.get(data.get('tef_out', 'Gold'), 0),
        'TARAGG': data.get('tariff', 120.0),
        'nss_average_satisfaction': data.get('nss', 85.0)
    }])
    predictions = {}
    for tn, model in ML_MODELS.items():
        try:
            predictions[tn] = float(model.predict(input_data)[0])
        except:
            predictions[tn] = None
    return jsonify({"predictions": predictions})

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=3000, debug=True)
