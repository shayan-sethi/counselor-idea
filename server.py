import os
import json
import datetime
import joblib
import pandas as pd
from flask import Flask, jsonify, request, send_from_directory
try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass

# ──────────────────────────────────────────────
#  PRISM Web API Server
# ──────────────────────────────────────────────

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
STUDENTS_PATH = os.path.join(BASE_DIR, "data", "students_db.json")

from prism_agent.knowledge_graph import KnowledgeGraph
from prism_agent.reasoner import Reasoner
from prism_agent.planner import Planner
from prism_agent.agent import PRISMAgent
from prism_agent.ingestion_agent import DocumentIngestionAgent
from prism_agent.board_converter import BoardGradeConverter

kg = KnowledgeGraph()
reasoner = Reasoner(kg)
planner = Planner()
agent = PRISMAgent(kg, reasoner, planner)
ingestion_agent = DocumentIngestionAgent()

# ── Portfolio auto-classifier ──
TIER_1_KEYWORDS = ["international", "olympiad", "patent", "published", "national award",
                   "research paper", "imo", "ioi", "usamo", "intel isef", "google science fair",
                   "national winner", "world", "global", "ieee", "arxiv"]
TIER_2_KEYWORDS = ["state", "regional", "founder", "president", "hackathon winner",
                   "mun best delegate", "national qualifier", "captain", "head boy",
                   "head girl", "ted talk", "startup", "state winner", "gold medal"]

def auto_classify_portfolio(portfolio):
    """Auto-classify portfolio activity tiers from descriptions using keyword rules."""
    classified = []
    for item in portfolio:
        text = (item.get("activity", "") + " " + item.get("description", "")).lower()
        if any(kw in text for kw in TIER_1_KEYWORDS):
            tier = 1
        elif any(kw in text for kw in TIER_2_KEYWORDS):
            tier = 2
        else:
            tier = item.get("tier", 3)  # Keep explicit tier if provided, else default 3
        classified.append({**item, "tier": tier})
    return classified

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
        "portfolio": auto_classify_portfolio(data.get("portfolio", [])),
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

    # Run compliance check using agent
    result = {
        "student_id": student["id"],
        "student_name": student["name"],
        "class_level": student["class_level"],
        "targets": {}
    }
    traces = {}
    for tid in targets:
        agent_res = agent.solve_goal(student["id"], tid, STUDENTS, silent=True)
        if agent_res:
            result["targets"][tid] = {
                "target_name": agent_res.get("target_name", "Target"),
                "track": agent_res.get("track", "UK"),
                "compliant": agent_res.get("compliant", False),
                "match_score": agent_res.get("match_score", 100),
                "risk_level": agent_res.get("risk_level", "Strong Match"),
                "urgency_score": agent_res.get("urgency_score", 0),
                "gaps": agent_res.get("gaps", []),
                "remediations": agent_res.get("remediations", [])
            }
            traces[tid] = agent_res.get("trace", [])

    return jsonify({"student": student, "audit": result, "traces": traces}), 201

# ── Agentic Automated Data Ingestion ──

@app.route("/api/ingest_documents", methods=["POST"])
def api_ingest_documents():
    uploaded_files = []
    if "files" in request.files:
        uploaded_files = request.files.getlist("files")
    elif "file" in request.files:
        uploaded_files = [request.files["file"]]

    if not uploaded_files or not any(f.filename for f in uploaded_files):
        return jsonify({"error": "No valid document files uploaded"}), 400

    file_contents = []
    file_names = []
    uploads_dir = os.path.join(BASE_DIR, "uploads")
    os.makedirs(uploads_dir, exist_ok=True)

    for f in uploaded_files:
        if f.filename:
            fname = f.filename
            content = f.read()
            file_contents.append(content)
            file_names.append(fname)
            save_path = os.path.join(uploads_dir, fname)
            with open(save_path, "wb") as out_f:
                out_f.write(content)

    extracted_profile = ingestion_agent.process_documents(file_contents, file_names)

    auto_save = request.form.get("auto_save", "true").lower() == "true"
    student_id = request.form.get("student_id", "").strip()

    if "id" not in extracted_profile:
        extracted_profile["id"] = student_id or "STU_PREVIEW"

    if auto_save:
        if not student_id or student_id == "STU_PREVIEW":
            student_id = next_student_id()
            extracted_profile["id"] = student_id
            if "status" not in extracted_profile:
                extracted_profile["status"] = {"cuet_form_submitted": False, "tmua_registered": False, "sat_score": None}
            STUDENTS.append(extracted_profile)
        else:
            idx = next((i for i, s in enumerate(STUDENTS) if s["id"] == student_id), None)
            if idx is not None:
                existing = STUDENTS[idx]
                existing.update(extracted_profile)
                existing["id"] = student_id
                extracted_profile = existing
            else:
                extracted_profile["id"] = student_id
                STUDENTS.append(extracted_profile)
        save_students(STUDENTS)

    evaluation = {}
    try:
        evaluation = reasoner.evaluate_student(extracted_profile)
    except Exception as eval_err:
        print(f"[Ingest Warning] Evaluation check warning: {eval_err}")

    return jsonify({
        "student": extracted_profile,
        "evaluation": evaluation,
        "extracted_from": file_names
    })

# ── Inter-Board Grade Standardization Endpoint ──

@app.route("/api/convert_grade", methods=["POST", "GET"])
def api_convert_grade():
    if request.method == "POST":
        data = request.get_json() or {}
        raw_grade = data.get("grade")
        board = data.get("board", "CBSE")
        class_level = int(data.get("class_level", 12))
    else:
        raw_grade = request.args.get("grade")
        board = request.args.get("board", "CBSE")
        class_level = int(request.args.get("class_level", 12))

    pct_equiv, level = BoardGradeConverter.convert_grade(raw_grade, class_level=class_level, board=board)
    return jsonify({
        "raw_grade": raw_grade,
        "class_level": class_level,
        "board": board,
        "percentage_equivalent": pct_equiv,
        "performance_level": level
    })

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

    # Run compliance check using agent
    result = {
        "student_id": student["id"],
        "student_name": student["name"],
        "class_level": student["class_level"],
        "targets": {}
    }
    traces = {}
    for tid in student.get("targets", []):
        agent_res = agent.solve_goal(student["id"], tid, STUDENTS, simulated_subjects=simulated_subjects, silent=True)
        if agent_res:
            result["targets"][tid] = {
                "target_name": agent_res.get("target_name", "Target"),
                "track": agent_res.get("track", "UK"),
                "compliant": agent_res.get("compliant", False),
                "match_score": agent_res.get("match_score", 100),
                "risk_level": agent_res.get("risk_level", "Strong Match"),
                "urgency_score": agent_res.get("urgency_score", 0),
                "gaps": agent_res.get("gaps", []),
                "remediations": agent_res.get("remediations", [])
            }
            traces[tid] = agent_res.get("trace", [])

    result["traces"] = traces
    return jsonify(result)

@app.route("/api/evaluate_cohort")
def api_evaluate_cohort():
    results = {}
    for student in STUDENTS:
        result = {
            "student_id": student["id"],
            "student_name": student["name"],
            "class_level": student["class_level"],
            "targets": {}
        }
        for tid in student.get("targets", []):
            agent_res = agent.solve_goal(student["id"], tid, STUDENTS, silent=True)
            if agent_res:
                result["targets"][tid] = {
                    "target_name": agent_res.get("target_name", "Target"),
                    "track": agent_res.get("track", "UK"),
                    "compliant": agent_res.get("compliant", False),
                    "match_score": agent_res.get("match_score", 100),
                    "risk_level": agent_res.get("risk_level", "Strong Match"),
                    "urgency_score": agent_res.get("urgency_score", 0),
                    "gaps": agent_res.get("gaps", []),
                    "remediations": agent_res.get("remediations", [])
                }
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

# ── Student Portal AI Copilot Advisor ──

@app.route("/api/student_advisor", methods=["POST"])
def api_student_advisor():
    data = request.get_json()
    student_id = data.get("student_id")
    message = data.get("message", "").lower()
    
    student = next((s for s in STUDENTS if s["id"] == student_id), None)
    if not student:
        return jsonify({"reply": "I couldn't find your profile. Please complete Step 1 first."})

    # Evaluate current targets
    student_gaps = []
    has_math_gap = False
    for tid in student.get("targets", []):
        agent_res = agent.solve_goal(student["id"], tid, STUDENTS, silent=True)
        if agent_res and not agent_res.get("compliant", False):
            for gap in agent_res.get("gaps", []):
                student_gaps.append(gap)
                if "math" in gap.get("subject", "").lower() or "mathematics" in gap.get("description", "").lower():
                    has_math_gap = True

    # Agentic reasoning response
    if "tmua" in message or "test" in message or "exam" in message:
        reply = (
            "🎯 **TMUA (Test of Mathematics for University Admission) Insights:**\n\n"
            "The TMUA is mandatory for Cambridge CS and Imperial Computing. It consists of two papers: \n"
            "1. **Mathematical Reasoning** (20 multiple choice questions, 75 mins)\n"
            "2. **Mathematical Speculation** (20 multiple choice questions, 75 mins)\n\n"
            "**Advisors Recommended Actions:**\n"
            "- Start preparing with past papers from the official Cambridge Admissions website.\n"
            "- Solve UKMT Senior Mathematical Challenge papers to build speed and logical analysis.\n"
            "- Double check the registration deadline: **September 16, 2026**."
        )
    elif "math" in message or "subject" in message:
        if has_math_gap:
            reply = (
                "⚠️ **Mathematics Requirement Alert:**\n\n"
                "Your profile currently shows a critical Mathematics prerequisite gap for your targets. "
                "Because CBSE/ICSE doesn't easily permit late subject additions in Class 12, here is your agentic action plan:\n\n"
                "1. **AP Calculus BC Override:** Register for AP Calculus BC in May to satisfy Cambridge CS/Imperial Math prerequisites.\n"
                "2. **Target List Pivoting:** Consider applying to courses like BA Business Administration or BCA, or private universities (e.g. Ashoka University) where Class 12 Math is not mandatory.\n"
                "3. **Board Registration Check:** Verify with your school counselor if it's still possible to register for Mathematics as a 6th subject."
            )
        else:
            reply = (
                "📚 **Subject Strategy advice:**\n\n"
                "Your current board subject registration matches your target pathways. Ensure you maintain at least **95% in Mathematics and Physics** if you are targeting elite UK pathways like Cambridge CS."
            )
    elif "portfolio" in message or "extracurricular" in message or "activity" in message:
        reply = (
            "🏆 **Extracurricular Portfolio Roadmap:**\n\n"
            "Our AI auto-classifier assesses the impact tier of your activities based on global reach. \n"
            "- **Tier 1 (elite):** Research papers (IEEE, arXiv), national olympiads (IMO, IOI), patent filings, or global startup launch.\n"
            "- **Tier 2 (strong):** State championships, regional hackathon winners, founding clubs, head boy/girl status.\n\n"
            "**Action Item:** If targeting US universities (Stanford, MIT), aim to convert one of your Tier 3 school activities into a Tier 1 or Tier 2 regional/national project."
        )
    else:
        gaps_summary = f"Currently, you have {len(student_gaps)} active gap(s) across your target pathways." if student_gaps else "Awesome! You are fully on track with no gaps."
        reply = (
            f"Hello {student.get('name')}! I am your PRISM Pathway Copilot. {gaps_summary}\n\n"
            "Ask me anything about:\n"
            "- **'TMUA preparation'** or registration timelines\n"
            "- **'Math requirements'** or board subject mismatch remediations\n"
            "- **'Portfolio projects'** to level up your extracurricular tier"
        )

    return jsonify({"reply": reply})

# ── Counselor Portal AI Cohort Command Center Agent ──

@app.route("/api/counselor_agent", methods=["POST"])
def api_counselor_agent():
    data = request.get_json()
    command = data.get("command", "").strip().lower()

    if "email" in command or "draft" in command:
        # Find students with critical gaps (Aarav, Dia, Rohan, etc.)
        flagged_students = []
        for s in STUDENTS:
            for tid in s.get("targets", []):
                res = agent.solve_goal(s["id"], tid, STUDENTS, silent=True)
                if res and not res.get("compliant", False):
                    flagged_students.append((s, res.get("gaps")[0]))
                    break # just need one gap to flag
        
        if not flagged_students:
            return jsonify({"response": "No students currently require warning emails."})

        # Draft email for the first flagged student as an example
        s, gap = flagged_students[0]
        draft = (
            f"### 📧 Draft Email for {s['name']} ({s['id']})\n\n"
            f"**To:** {s['name'].lower().replace(' ', '.')}@school.edu\n"
            f"**Subject:** Action Required: Urgent Correction on Pathway Target Prerequisite Mismatch\n\n"
            f"Dear {s['name']},\n\n"
            f"We reviewed your academic profile and targets using the PRISM Compliance Agent. We noticed a **CRITICAL** gap:\n"
            f"👉 *{gap.get('description')}*\n\n"
            f"Please schedule a meeting with the counselor office this week to discuss target remediation (e.g. correcting your registration or adjusting target universities).\n\n"
            f"Best regards,\n"
            f"School College Counseling Center"
        )
        return jsonify({"response": draft})

    elif "recommend" in command or "suggest" in command or "stu_" in command:
        # Extract student ID or name
        student_match = re.search(r'(stu_\d+)', command)
        student_id = student_match.group(1).upper() if student_match else "STU_001"
        s = next((st for st in STUDENTS if st["id"] == student_id), None)
        
        if not s:
            return jsonify({"response": f"Student with ID '{student_id}' not found."})

        # Run compliance check against all pathways in database to find recommendations
        all_targets = kg.get_all_targets()
        recs = []
        for target in all_targets:
            # Skip targets student is already aiming for
            if target["id"] in s.get("targets", []):
                continue
            res = agent.solve_goal(s["id"], target["id"], STUDENTS, silent=True)
            recs.append((target, res.get("match_score", 100)))
        
        recs.sort(key=lambda x: x[1], reverse=True)
        top_recs = recs[:3]
        
        resp = f"### 🎯 Target Recommendations for {s['name']} ({s['id']})\n\n"
        for t, score in top_recs:
            resp += f"- **{t['name']}** (Match Score: **{score}%**)\n  *Reasoning:* Prerequisite compliance aligns well with {s['board']} curriculum.\n"
        return jsonify({"response": resp})

    else:
        # Default Cohort Risk Summary Report
        high_risk_count = 0
        total_students = len(STUDENTS)
        common_gaps = {}
        
        for s in STUDENTS:
            min_match = 100
            for tid in s.get("targets", []):
                res = agent.solve_goal(s["id"], tid, STUDENTS, silent=True)
                if res:
                    min_match = min(min_match, res.get("match_score", 100))
                    for gap in res.get("gaps", []):
                        common_gaps[gap.get("subject", "General")] = common_gaps.get(gap.get("subject", "General"), 0) + 1
            if min_match < 70:
                high_risk_count += 1

        common_gaps_sorted = sorted(common_gaps.items(), key=lambda x: x[1], reverse=True)[:3]
        gaps_list = ", ".join([f"{k} ({v} students)" for k, v in common_gaps_sorted])

        resp = (
            "### 📊 PRISM Cohort Risk Analysis Report\n\n"
            f"- **Cohort Size:** {total_students} active students\n"
            f"- **High-Risk Students:** **{high_risk_count}** students with match scores < 70%\n"
            f"- **Most Common Prerequisite Gaps:** {gaps_list if gaps_list else 'None'}\n\n"
            "**Suggested Counselor Interventions:**\n"
            "1. Hold a group workshop for students missing Mathematics.\n"
            "2. Send bulk warning email drafts to high-risk students."
        )
        return jsonify({"response": resp})

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=3000, debug=True)
