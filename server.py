import sys
import os
import json
import datetime
import joblib
import pandas as pd
try:
    import google.generativeai as genai
except ImportError:
    genai = None
from flask import Flask, jsonify, request, send_from_directory
try:
    from dotenv import load_dotenv
    load_dotenv(override=True)
except ImportError:
    pass

env_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), ".env")
if os.path.exists(env_path):
    with open(env_path, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if line and not line.startswith("#") and "=" in line:
                k, v = line.split("=", 1)
                os.environ[k.strip()] = v.strip().strip('"').strip("'")

if hasattr(sys.stdout, 'reconfigure'):
    sys.stdout.reconfigure(encoding='utf-8')
if hasattr(sys.stderr, 'reconfigure'):
    sys.stderr.reconfigure(encoding='utf-8')


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
from prism_agent.opportunity_radar import OpportunityRadar, CompeteMapScraper
from prism_agent.scholarship_agent import ScholarshipAgent

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

print("[+] unlockED engine + ML models loaded.")

# ──────────────────────────────────────────────
#  Flask App
# ──────────────────────────────────────────────

from flask import session, redirect, url_for
import hashlib
from functools import wraps

app = Flask(__name__, static_folder="static", static_url_path="/static")
app.secret_key = "prism-secure-secret-key-12345"
app.config['SEND_FILE_MAX_AGE_DEFAULT'] = 0

USERS_PATH = os.path.join(BASE_DIR, "data", "users_db.json")

def load_users():
    if os.path.exists(USERS_PATH):
        with open(USERS_PATH, "r") as f:
            return json.load(f)
    return []

def save_users(users):
    with open(USERS_PATH, "w") as f:
        json.dump(users, f, indent=2)

def hash_password(password):
    return hashlib.sha256(password.encode('utf-8')).hexdigest()

# ── Auth Decorators ──

def login_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if "username" not in session:
            return jsonify({"error": "Unauthorized. Please log in."}), 401
        return f(*args, **kwargs)
    return decorated_function

def counselor_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if "username" not in session:
            return jsonify({"error": "Unauthorized. Please log in."}), 401
        if session.get("role") != "counselor":
            return jsonify({"error": "Forbidden. Counselor role required."}), 403
        return f(*args, **kwargs)
    return decorated_function

def student_self_only(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if "username" not in session:
            return jsonify({"error": "Unauthorized. Please log in."}), 401
        role = session.get("role")
        if role == "counselor":
            return f(*args, **kwargs)
        
        # Determine student_id from route kwargs or JSON body or query param
        student_id = kwargs.get("student_id")
        if not student_id and request.is_json:
            student_id = request.get_json().get("student_id")
        if not student_id:
            student_id = request.args.get("student_id")
            
        if role == "student" and session.get("student_id") != student_id:
            return jsonify({"error": "Forbidden. You can only access your own profile."}), 403
        return f(*args, **kwargs)
    return decorated_function

# ── Security Headers ──

@app.after_request
def add_security_headers(response):
    response.headers['X-Content-Type-Options'] = 'nosniff'
    response.headers['X-Frame-Options'] = 'DENY'
    response.headers['X-XSS-Protection'] = '1; mode=block'
    response.headers['Content-Security-Policy'] = "default-src 'self'; script-src 'self' 'unsafe-inline'; style-src 'self' 'unsafe-inline' https://fonts.googleapis.com; font-src 'self' https://fonts.gstatic.com; connect-src 'self';"
    return response

# ── Auth Endpoints ──

@app.route("/api/login", methods=["POST"])
def api_login():
    data = request.get_json()
    if not data:
        return jsonify({"error": "Missing login credentials"}), 400
    username = data.get("username", "").strip()
    password = data.get("password", "").strip()
    
    users = load_users()
    user = next((u for u in users if u["username"].lower() == username.lower()), None)
    if not user or user["password_hash"] != hash_password(password):
        return jsonify({"error": "Invalid username or password"}), 401
    
    session["username"] = user["username"]
    session["role"] = user["role"]
    session["student_id"] = user["student_id"]
    
    return jsonify({
        "message": "Login successful",
        "role": user["role"],
        "student_id": user["student_id"],
        "username": user["username"]
    })

@app.route("/api/signup", methods=["POST"])
def api_signup():
    data = request.get_json()
    if not data:
        return jsonify({"error": "Missing data"}), 400
    username = data.get("username", "").strip()
    password = data.get("password", "").strip()
    wizardData = data.get("wizardData")
    
    if not username or not password:
        return jsonify({"error": "Username and password required"}), 400
        
    users = load_users()
    if any(u["username"].lower() == username.lower() for u in users):
        return jsonify({"error": "Username already exists"}), 400
        
    new_student_id = next_student_id()
    
    new_user = {
        "username": username,
        "password_hash": hash_password(password),
        "role": "student",
        "student_id": new_student_id
    }
    users.append(new_user)
    save_users(users)
    
    # Create student profile from wizardData
    student_name = username
    class_level = 12
    board = "CBSE"
    board_subjects = ["Physics", "Chemistry", "Mathematics", "English"]
    cuet_subjects = ["Physics", "Chemistry", "Mathematics", "English"]
    grades = {}
    standardized_tests = {}
    portfolio = []
    targets = []
    shortlisted_colleges = []
    
    if wizardData:
        # 1. Map Grade Level (step_1)
        grade_str = wizardData.get("step_1", "")
        if "9th" in grade_str: class_level = 9
        elif "10th" in grade_str: class_level = 10
        elif "11th" in grade_str: class_level = 11
        elif "12th" in grade_str: class_level = 12
        
        # 2. Map Board (step_2)
        board = wizardData.get("step_2", "CBSE")
        
        # 3. Map Grades (step_3)
        g_str = wizardData.get("step_3", "")
        if g_str:
            grades = {
                "class_10_aggregate": g_str,
                "class_11_aggregate": g_str,
                "current_expected_board": g_str,
                "subjects": {}
            }
            
        # 4. Map SAT (step_4)
        sat_str = wizardData.get("step_4", "")
        if "1500" in sat_str:
            standardized_tests["SAT"] = 1520
        elif "1300" in sat_str:
            standardized_tests["SAT"] = 1380
        elif "Below 1300" in sat_str:
            standardized_tests["SAT"] = 1200
            
        # 5. Map Extracurriculars (step_5)
        ec_str = wizardData.get("step_5", "")
        if ec_str:
            portfolio.append({
                "activity": "Extracurricular Focus",
                "description": ec_str
            })
            
        # 6. Map Intended Major (step_6)
        major = wizardData.get("step_6", "")
        if major in ["Computer Science", "Engineering"]:
            board_subjects = ["Physics", "Chemistry", "Computer Science", "English"]
            cuet_subjects = ["Physics", "Chemistry", "Mathematics", "English"]
        elif major == "Pre-Med & Healthcare":
            board_subjects = ["Physics", "Chemistry", "Biology", "English"]
            cuet_subjects = ["Physics", "Chemistry", "Biology", "English"]
        elif major in ["Business & Finance", "Economics"]:
            board_subjects = ["Economics", "Mathematics", "Business Studies", "English"]
            cuet_subjects = ["Economics", "Mathematics", "Business Studies", "English"]
        else:
            board_subjects = ["History", "Political Science", "Economics", "English"]
            cuet_subjects = ["History", "Political Science", "Economics", "English"]
            
        # 7. Map Target Colleges (step_9)
        country = wizardData.get("step_9", "")
        if "US" in country:
            shortlisted_colleges = ["MIT", "STANFORD"]
        elif "UK" in country:
            shortlisted_colleges = ["CAMBRIDGE", "OXFORD", "IMPERIAL"]
        elif "India" in country:
            shortlisted_colleges = ["DU", "ASHOKA"]
            if major in ["Computer Science", "Engineering"]:
                targets = ["CUET_DU_CS"]
            else:
                targets = ["CUET_DU_ECO"]
        else:
            shortlisted_colleges = ["MIT", "CAMBRIDGE", "ASHOKA"]
            
        if "UK" in country and major in ["Computer Science", "Engineering"]:
            targets = ["CAMBRIDGE_CS"]
        
    new_student = {
        "id": new_student_id,
        "name": student_name,
        "class_level": class_level,
        "board": board,
        "board_subjects": board_subjects,
        "cuet_subjects": cuet_subjects,
        "grades": grades,
        "standardized_tests": standardized_tests,
        "portfolio": portfolio,
        "targets": targets,
        "shortlisted_colleges": shortlisted_colleges,
        "status": {
            "cuet_form_submitted": False,
            "tmua_registered": False,
            "sat_score": None
        }
    }
    STUDENTS.append(new_student)
    save_students(STUDENTS)
    
    session["username"] = new_user["username"]
    session["role"] = new_user["role"]
    session["student_id"] = new_user["student_id"]
    
    return jsonify({
        "message": "Signup successful",
        "role": new_user["role"],
        "student_id": new_user["student_id"],
        "username": new_user["username"]
    })

@app.route("/api/logout", methods=["POST", "GET"])
def api_logout():
    session.clear()
    return jsonify({"message": "Logged out successfully"})

@app.route("/api/user_session")
def api_user_session():
    if "username" not in session:
        return jsonify({"authenticated": False}), 200
    return jsonify({
        "authenticated": True,
        "username": session["username"],
        "role": session["role"],
        "student_id": session["student_id"]
    })

# ── Page routes ──

@app.route("/")
def landing_page():
    return send_from_directory("static", "landing.html")

@app.route("/dashboard")
def counselor_dashboard():
    if "username" not in session:
        return redirect("/static/login.html")
    if session.get("role") != "counselor":
        return redirect("/student")
    return send_from_directory("static", "index.html")

@app.route("/student")
def student_portal():
    if "username" not in session:
        return redirect("/static/login.html")
    return send_from_directory("static", "student.html")

# ── Read endpoints ──

@app.route("/api/students")
@counselor_required
def api_students():
    return jsonify(STUDENTS)

@app.route("/api/student/<student_id>")
@student_self_only
def api_student_single(student_id):
    s = next((s for s in STUDENTS if s["id"] == student_id), None)
    if not s:
        return jsonify({"error": "Not found"}), 404
    return jsonify(s)

@app.route("/api/targets")
@login_required
def api_targets():
    return jsonify(kg.requirements)

@app.route("/api/targets", methods=["POST"])
@counselor_required
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
@counselor_required
def api_delete_target(target_id):
    if target_id not in kg.requirements:
        return jsonify({"error": "Target not found"}), 404
    
    del kg.requirements[target_id]
    with open(kg.db_path, "w") as f:
        json.dump(kg.requirements, f, indent=2)
    
    kg.load_database()
    return jsonify({"ok": True})

@app.route("/api/model_metrics")
@login_required
def api_model_metrics():
    return jsonify(MODEL_METRICS)

# ── Create student ──

# ── UK Course Database Search Endpoints ──

COLLEGES_CACHE = None

SEARCH_UNIS_CACHE = None
def get_search_unis_data():
    global SEARCH_UNIS_CACHE
    if SEARCH_UNIS_CACHE is not None:
        return SEARCH_UNIS_CACHE

    uk_df_path = os.path.join(BASE_DIR, "data", "cleaned_courses_dataset.csv")
    us_df_path = os.path.join(BASE_DIR, "data", "cleaned_us_colleges.csv")
    ind_json_path = os.path.join(BASE_DIR, "data", "indian_unis.json")

    unis_list = []
    
    # UK
    if os.path.exists(uk_df_path):
        df_uk = pd.read_csv(uk_df_path, usecols=["LEGAL_NAME"])
        uk_unis = df_uk["LEGAL_NAME"].dropna().unique()
        unis_list.extend([{"name": str(u), "country": "UK"} for u in uk_unis])
        
    # US
    if os.path.exists(us_df_path):
        df_us = pd.read_csv(us_df_path, usecols=["INSTNM"])
        us_unis = df_us["INSTNM"].dropna().unique()
        unis_list.extend([{"name": str(u), "country": "US"} for u in us_unis])
        
    # India
    if os.path.exists(ind_json_path):
        with open(ind_json_path, "r", encoding="utf-8") as f:
            ind_data = json.load(f)
            ind_unis = [u["name"] for u in ind_data]
            unis_list.extend([{"name": str(u), "country": "India"} for u in ind_unis])
            
    SEARCH_UNIS_CACHE = sorted(unis_list, key=lambda x: x["name"])
    return SEARCH_UNIS_CACHE

SEARCH_COURSES_DF_CACHE = None
def get_courses_df():
    global SEARCH_COURSES_DF_CACHE
    if SEARCH_COURSES_DF_CACHE is not None:
        return SEARCH_COURSES_DF_CACHE
    df_path = os.path.join(BASE_DIR, "data", "cleaned_courses_dataset.csv")
    if os.path.exists(df_path):
        SEARCH_COURSES_DF_CACHE = pd.read_csv(df_path, usecols=["LEGAL_NAME", "TITLE", "TARAGG", "sbj_group"])
    return SEARCH_COURSES_DF_CACHE

@app.route("/api/search_unis")
@login_required
def api_search_unis():
    query = request.args.get("q", "").strip().lower()
    try:
        all_unis = get_search_unis_data()
        if query:
            results = [u for u in all_unis if query in u["name"].lower()]
        else:
            results = all_unis[:50]
        return jsonify(results[:50] if query else results)
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route("/api/search_courses")
@login_required
def api_search_courses():
    uni = request.args.get("uni", "").strip()
    query = request.args.get("q", "").strip().lower()
    
    # Quick check for Indian
    ind_json_path = os.path.join(BASE_DIR, "data", "indian_unis.json")
    if os.path.exists(ind_json_path):
        with open(ind_json_path, "r", encoding="utf-8") as f:
            ind_data = json.load(f)
            for u in ind_data:
                if u["name"].lower() == uni.lower():
                    results = [{"title": c, "subject_group": None, "tariff": None} for c in u.get("courses", [])]
                    if query:
                        results = [r for r in results if query in r["title"].lower()]
                    return jsonify(results)
                    
    # Quick check for US
    all_unis = get_search_unis_data()
    if any(u["name"].lower() == uni.lower() and u["country"] == "US" for u in all_unis):
        return jsonify([{"title": "Undergraduate Bachelors Program", "subject_group": "Generic", "tariff": None}])

    # UK
    df = get_courses_df()
    if df is None or df.empty:
        return jsonify([])

    try:
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
                "remediations": agent_res.get("remediations", []),
                "difficulty_label": agent_res.get("difficulty_label", "Target")
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
@login_required
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

@app.route("/api/students/<student_id>", methods=["GET", "PUT"])
@student_self_only
def api_update_student(student_id):
    if request.method == "GET":
        student = next((s for s in STUDENTS if s["id"] == student_id), None)
        if not student:
            return jsonify({"error": "Student not found"}), 404
        return jsonify(student)

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
                  "planned_class_11_subjects", "counselor_notes", "shortlisted_colleges"]:
        if field in data:
            student[field] = data[field]

    if "class_level" in data:
        student["class_level"] = int(data["class_level"])

    STUDENTS[idx] = student
    save_students(STUDENTS)
    return jsonify({"student": student})

# ── Delete student ──

@app.route("/api/students/<student_id>", methods=["DELETE"])
@counselor_required
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
@student_self_only
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
        agent_res = agent.solve_goal(student["id"], tid, STUDENTS, simulated_subjects=simulated_subjects, silent=True, use_real_engine=True)
        if agent_res:
            result["targets"][tid] = {
                "target_name": agent_res.get("target_name", "Target"),
                "track": agent_res.get("track", "UK"),
                "compliant": agent_res.get("compliant", False),
                "match_score": agent_res.get("match_score", 100),
                "risk_level": agent_res.get("risk_level", "Strong Match"),
                "urgency_score": agent_res.get("urgency_score", 0),
                "gaps": agent_res.get("gaps", []),
                "remediations": agent_res.get("remediations", []),
                "difficulty_label": agent_res.get("difficulty_label", "Target")
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
            try:
                import time
                time.sleep(0.15)  # Artificial delay to simulate agent reasoning
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
                        "remediations": agent_res.get("remediations", []),
                        "difficulty_label": agent_res.get("difficulty_label", "Target")
                    }
            except Exception as e:
                # If Gemini hits a rate limit or errors, provide a safe fallback so the dashboard doesn't crash
                print(f"Error evaluating {student['id']} for {tid}: {e}")
                result["targets"][tid] = {
                    "target_name": "API Rate Limit / Engine Unavailable",
                    "track": "Unknown",
                    "compliant": False,
                    "match_score": 0,
                    "risk_level": "Engine Offline",
                    "urgency_score": 0,
                    "gaps": [{"field": "System", "issue": "Gemini API rate limit exceeded. Please wait a minute and refresh."}],
                    "remediations": [],
                    "difficulty_label": "Unknown"
                }
        results[student["id"]] = result
    return jsonify(results)

# ── ML Predict ──

@app.route("/api/predict", methods=["POST"])
@login_required
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
@student_self_only
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
            f"Hello {student.get('name')}! I am your unlockED Pathway Copilot. {gaps_summary}\n\n"
            "Ask me anything about:\n"
            "- **'TMUA preparation'** or registration timelines\n"
            "- **'Math requirements'** or board subject mismatch remediations\n"
            "- **'Portfolio projects'** to level up your extracurricular tier"
        )

    return jsonify({"reply": reply})

# ── Counselor Portal AI Cohort Command Center Agent ──

@app.route("/api/counselor_agent", methods=["POST"])
def api_counselor_agent():
    data = request.get_json() or {}
    command = data.get("command", "").strip()
    if not command:
        return jsonify({"response": "Please enter a counselor command or query."}), 400

    api_key = os.environ.get("GEMINI_API_KEY", "")
    
    # Compile live cohort context for reasoning model
    cohort_summary_list = []
    for s in STUDENTS:
        student_audits = {}
        for tid in s.get("targets", []):
            try:
                tid_str = tid.get("id", tid) if isinstance(tid, dict) else tid
                audit_res = agent.solve_goal(s["id"], tid_str, STUDENTS, silent=True)
                if audit_res:
                    student_audits[str(tid_str)] = {
                        "match_score": audit_res.get("match_score", 100),
                        "compliant": audit_res.get("compliant", True),
                        "gaps": audit_res.get("gaps", []),
                        "remediations": audit_res.get("remediations", [])
                    }
            except Exception:
                pass
        cohort_summary_list.append({
            "id": s["id"],
            "name": s["name"],
            "board": s.get("board"),
            "class_level": s.get("class_level"),
            "board_subjects": s.get("board_subjects", []),
            "grades": s.get("grades", {}),
            "standardized_tests": s.get("standardized_tests", {}),
            "portfolio": s.get("portfolio", []),
            "targets": s.get("targets", []),
            "audits": student_audits
        })

    system_prompt = f"""You are the unlockED Counselor AI Agent & Chief Admissions Officer Co-Pilot.
You have access to the entire school's active student cohort database provided below.

STUDENT COHORT DATA:
{json.dumps(cohort_summary_list, indent=2)}

CRITICAL REASONING INSTRUCTIONS:
1. Act as a highly intelligent, expert high school counselor and admissions strategist.
2. Analyze the counselor's prompt carefully. It may ask you to:
   - Perform a risk audit or cohort gap analysis across all students.
   - Draft personalized warning or guidance emails to specific students or parents.
   - Recommend new target pathways, university choices, or portfolio improvements for a specific student (e.g. STU_001).
   - Provide strategic interventions, deadline warnings, or custom counseling notes.
3. NEVER return static hardcoded canned responses. Always analyze the actual live JSON student cohort data dynamically.
4. Format your output in clean Markdown with appropriate headers, bold text, bullet points, and actionable details.
5. If drafting an email, include Subject line, To address, Salutation, specific student gap evidence, and professional sign-off.
"""
    if api_key:
        try:
            import google.generativeai as genai
            genai.configure(api_key=api_key)
            
            for m_name in ["gemini-3.6-flash", "gemini-2.5-flash", "gemini-2.0-flash", "gemini-3.5-flash", "gemini-flash-latest", "gemini-2.0-flash-lite"]:
                try:
                    model = genai.GenerativeModel(model_name=m_name)
                    response = model.generate_content([system_prompt, f"COUNSELOR PROMPT / COMMAND:\n{command}"])
                    if response and response.text:
                        return jsonify({"response": response.text.strip()})
                except Exception as m_err:
                    print(f"[CounselorAgent Warning] Model {m_name} rate limited/failed: {m_err}. Trying next candidate...")
        except Exception as err:
            print(f"[CounselorAgent Error] Gemini reasoning model call failed: {err}")

    # Fallback to local Ollama engine if Gemini is not configured or fails
    import requests
    try:
        ollama_res = requests.post("http://127.0.0.1:11434/api/generate", json={
            "model": "llama3.2",
            "prompt": f"{system_prompt}\n\nCOUNSELOR PROMPT / COMMAND:\n{command}",
            "stream": False,
            "options": {"temperature": 0.3}
        }, timeout=45)
        if ollama_res.status_code == 200:
            return jsonify({"response": ollama_res.json().get("response", "").strip()})
    except Exception as e:
        print(f"[CounselorAgent Warning] Local Ollama fallback failed: {e}")

    # Final hardcoded fallback if everything else fails
    command_lower = command.lower()
    if "email" in command_lower or "draft" in command_lower:
        flagged = [s for s in cohort_summary_list if any(not a.get("compliant") for a in s["audits"].values())]
        if not flagged:
            return jsonify({"response": "### 📧 Email Assistant\n\nNo students currently require urgent warning emails."})
        target_student = flagged[0]
        first_gap = next((g for a in target_student["audits"].values() for g in a.get("gaps", [])), {})
        draft = (
            f"### 📧 Dynamically Generated Warning Draft for {target_student['name']} ({target_student['id']})\n\n"
            f"**To:** {target_student['name'].lower().replace(' ', '.')}@school.edu\n"
            f"**Subject:** Action Required: Urgent Pathway Prerequisite Gap ({first_gap.get('subject', 'Academic Mismatch')})\n\n"
            f"Dear {target_student['name']},\n\n"
            f"Our unlockED compliance audit detected an active prerequisite gap for your target university pathways:\n"
            f"👉 *{first_gap.get('description', 'Prerequisite subject or grade cutoff missing.')}*\n\n"
            f"Please schedule a consultation with your school counselor to adjust your subject selection or pathway targets.\n\n"
            f"Best regards,\nSchool Counseling Office"
        )
        return jsonify({"response": draft})
    
    elif "recommend" in command_lower or "suggest" in command_lower or "stu_" in command_lower:
        student_match = re.search(r'(stu_\d+)', command_lower)
        sid = student_match.group(1).upper() if student_match else "STU_001"
        s = next((st for st in cohort_summary_list if st["id"] == sid), cohort_summary_list[0] if cohort_summary_list else None)
        if not s:
            return jsonify({"response": f"Student ID '{sid}' not found."})
        
        resp = f"### 🎯 Strategic University & Pathway Recommendations for {s['name']} ({s['id']})\n\n"
        resp += f"**Academic Board:** {s['board']} (Class {s['class_level']}) | **Current Targets:** {', '.join(s['targets']) or 'None'}\n\n"
        resp += f"1. **High-Fit Pathway Optimization:** Ensure studied subjects ({', '.join(s['board_subjects'])}) are mapped to domain prerequisites.\n"
        resp += f"2. **Portfolio Scaling:** {len(s['portfolio'])} activities registered. Focus on achieving Tier 1 national/international recognition.\n"
        return jsonify({"response": resp})
        
    else:
        total = len(cohort_summary_list)
        high_risk = sum(1 for s in cohort_summary_list if any(a.get("match_score", 100) < 70 for a in s["audits"].values()))
        resp = (
            f"### 📊 Live Cohort Risk & Compliance Analysis\n\n"
            f"- **Active Cohort Size:** {total} students evaluated\n"
            f"- **High Risk Count (<70% match):** **{high_risk}** student(s)\n\n"
            f"**Recommended Actions:**\n"
            f"1. Run targeted subject remediation workshops for flagged students.\n"
            f"2. Use command `draft warning emails` to auto-generate warning communications."
        )
        return jsonify({"response": resp})

# ── Opportunity Radar & Competition Monitor Endpoints ──

COMPETITIONS_PATH = os.path.join(BASE_DIR, "data", "competitions_db.json")

def load_competitions():
    if os.path.exists(COMPETITIONS_PATH):
        with open(COMPETITIONS_PATH, "r") as f:
            return json.load(f)
    return []

def save_competitions(comps):
    with open(COMPETITIONS_PATH, "w") as f:
        json.dump(comps, f, indent=2)

@app.route("/api/opportunities/<student_id>")
@student_self_only
def api_opportunities(student_id):
    student = next((s for s in STUDENTS if s["id"] == student_id), None)
    if not student:
        return jsonify({"error": "Student not found"}), 404
        
    competitions = load_competitions()
    matches = OpportunityRadar.match_student(student, competitions)
    return jsonify(matches)

@app.route("/api/import_competition", methods=["POST"])
@counselor_required
def api_import_competition():
    data = request.get_json()
    if not data or "url" not in data:
        return jsonify({"error": "URL is required"}), 400
        
    url = data["url"].strip()
    imported_comp = CompeteMapScraper.scrape_url(url)
    if not imported_comp:
        return jsonify({"error": "Failed to scrape competition details. Make sure the URL is a valid CompeteMap competition link."}), 400
        
    comps = load_competitions()
    idx = next((i for i, c in enumerate(comps) if c["id"] == imported_comp["id"]), None)
    if idx is not None:
        comps[idx] = imported_comp
    else:
        comps.append(imported_comp)
        
    save_competitions(comps)
    return jsonify(imported_comp), 201

@app.route("/api/competitions")
@login_required
def api_competitions():
    return jsonify(load_competitions())

@app.route("/api/shortlist/<student_id>", methods=["POST"])
@counselor_required
def api_shortlist_toggle(student_id):
    data = request.get_json()
    college_id = data.get("college_id")
    if not college_id:
        return jsonify({"error": "college_id required"}), 400

    idx = next((i for i, s in enumerate(STUDENTS) if s["id"] == student_id), None)
    if idx is None:
        return jsonify({"error": "Student not found"}), 404

    student = STUDENTS[idx]
    shortlisted = student.get("shortlisted_colleges", [])

    if college_id in shortlisted:
        shortlisted.remove(college_id)
        added = False
    else:
        shortlisted.append(college_id)
        added = True

    student["shortlisted_colleges"] = shortlisted
    STUDENTS[idx] = student
    save_students(STUDENTS)
    return jsonify({"added": added, "shortlisted_colleges": shortlisted})

# ── College Shortlist & Deadline Calendar Endpoints ──

COLLEGES_PATH = os.path.join(BASE_DIR, "data", "colleges_db.json")
EXAMS_PATH = os.path.join(BASE_DIR, "data", "exams_db.json")

def load_colleges():
    global COLLEGES_CACHE
    if COLLEGES_CACHE is not None:
        return COLLEGES_CACHE

    # Base colleges from colleges_db.json
    colleges = []
    if os.path.exists(COLLEGES_PATH):
        with open(COLLEGES_PATH, "r", encoding="utf-8") as f:
            colleges.extend(json.load(f))
            
    # Add Indian
    ind_json_path = os.path.join(BASE_DIR, "data", "indian_unis.json")
    if os.path.exists(ind_json_path):
        with open(ind_json_path, "r", encoding="utf-8") as f:
            ind_data = json.load(f)
            for item in ind_data:
                if not any(c["id"] == item["id"] for c in colleges):
                    colleges.append(item)
                    
    # Add US
    us_df_path = os.path.join(BASE_DIR, "data", "cleaned_us_colleges.csv")
    if os.path.exists(us_df_path):
        df_us = pd.read_csv(us_df_path)
        for _, row in df_us.iterrows():
            cid = f"US_{row['UNITID']}"
            name = str(row['INSTNM'])
            if not any(c["name"] == name for c in colleges):
                try:
                    deadlines = json.loads(str(row.get('DEADLINES', '[]')))
                except:
                    deadlines = []
                try:
                    subject_requirements = json.loads(str(row.get('SUBJECT_REQUIREMENTS', '[]')))
                except:
                    subject_requirements = []
                try:
                    required_exams = json.loads(str(row.get('REQUIRED_EXAMS', '[]')))
                except:
                    required_exams = []

                colleges.append({
                    "id": cid,
                    "name": name,
                    "country": "US",
                    "courses": ["Undergraduate Program"],
                    "deadlines": deadlines,
                    "required_exams": required_exams,
                    "subject_requirements": subject_requirements,
                    "expected_sat": str(int(row["SAT_AVG"])) if pd.notna(row.get("SAT_AVG")) and str(row.get("SAT_AVG")) not in ["N/A", "nan"] else "N/A"
                })
                
    # Add UK
    uk_df_path = os.path.join(BASE_DIR, "data", "cleaned_courses_dataset.csv")
    if os.path.exists(uk_df_path):
        df_uk = pd.read_csv(uk_df_path, usecols=["LEGAL_NAME"]).drop_duplicates()
        for _, row in df_uk.iterrows():
            name = str(row["LEGAL_NAME"])
            if pd.isna(name) or name == "nan": continue
            import re
            cid = f"UK_{re.sub(r'[^A-Z0-9]', '', name.upper())}"
            if not any(c["name"] == name for c in colleges):
                colleges.append({
                    "id": cid,
                    "name": name,
                    "country": "UK",
                    "courses": ["Various Programs"],
                    "deadlines": [],
                    "required_exams": []
                })
                
    COLLEGES_CACHE = colleges
    return colleges

def load_exams():
    if os.path.exists(EXAMS_PATH):
        with open(EXAMS_PATH, "r") as f:
            return json.load(f)
    return []

@app.route("/api/colleges")
@login_required
def api_colleges():
    return jsonify(load_colleges())

@app.route("/api/evaluate_shortlist", methods=["POST"])
@login_required
def api_evaluate_shortlist():
    data = request.json
    student_id = data.get("student_id")
    college_id = data.get("college_id")

    student = next((s for s in STUDENTS if s["id"] == student_id), None)
    if not student:
        return jsonify({"error": "Student not found"}), 404
        
    colleges = load_colleges()
    college = next((c for c in colleges if c["id"] == college_id), None)
    
    if not college:
        return jsonify({"category": "Target"})

    grades_dict = student.get("grades", {})
    grade = grades_dict.get("current_expected_board") or grades_dict.get("class_12_aggregate") or grades_dict.get("class_10_aggregate") or "80"
    
    grade_str = str(grade).replace('%','').strip()
    if '-' in grade_str:
        parts = grade_str.split('-')
        try:
            grade_val = sum(float(p.strip()) for p in parts) / len(parts)
        except:
            grade_val = 80.0
    else:
        try:
            grade_val = float(grade_str)
        except:
            grade_val = 80.0
        
    tests_dict = student.get("standardized_tests", {})
    sat = tests_dict.get("SAT") or tests_dict.get("sat")
    try:
        sat_val = int(sat)
    except:
        sat_val = 0

    name = college.get("name", "").lower()

    # Load Gemini university tiers cache
    tiers_path = os.path.join(BASE_DIR, "data", "university_tiers.json")
    tier_cache = {}
    if os.path.exists(tiers_path):
        try:
            with open(tiers_path, "r", encoding="utf-8") as f:
                tier_cache = json.load(f)
        except Exception:
            pass

    # Determine tier (1=Elite, 2=Top, 3=Strong, 4=Standard)
    # Default to hardcoded fallback lists if not yet in cache
    tier = tier_cache.get(name)

    if tier is None:
        try:
            import requests, re
            ollama_prompt = f"""You are a university ranking expert. Classify "{name}" into exactly one tier number (1, 2, 3, or 4).
1 = Elite (Oxford, Harvard, MIT, etc.)
2 = Top (UCL, Cornell, UCLA, NYU, etc.)
3 = Strong (Purdue, UT Austin, etc.)
4 = Standard (Regional/others)
Output ONLY a single integer (1, 2, 3, or 4)."""
            res = requests.post("http://127.0.0.1:11434/api/generate", json={
                "model": "llama3.2",
                "prompt": ollama_prompt,
                "stream": False,
                "options": {"temperature": 0.0}
            }, timeout=5)
            text = res.json().get("response", "").strip()
            # Extract the first digit found
            match = re.search(r'\d', text)
            if match:
                tier = int(match.group(0))
            else:
                raise ValueError("No digit in Ollama response")
        except Exception as e:
            # Complete fallback to hardcoded list if Ollama fails
            print(f"[Ollama Fallback Error] {e}")
            ELITE = ["harvard", "yale", "stanford", "mit", "princeton", "caltech", "cambridge", "oxford", "imperial", "eth zurich", "lse", "chicago", "columbia"]
            TOP = ["cornell", "ucl", "ucla", "uc berkeley", "michigan", "nyu", "toronto", "melbourne", "edinburgh", "duke", "johns hopkins"]
            STRONG = ["purdue", "umass", "ut austin", "ohio state", "penn state", "arizona state", "illinois", "wisconsin", "georgia tech"]
            
            if any(x in name for x in ELITE):
                tier = 1
            elif any(x in name for x in TOP):
                tier = 2
            elif any(x in name for x in STRONG):
                tier = 3
            else:
                tier = 4

    # Classify Reach / Target / Safety based on Tier
    if tier == 1: # Elite
        if grade_val >= 98 and sat_val >= 1560:
            category = "Target"
        else:
            category = "Reach"
    elif tier == 2: # Top
        if grade_val >= 95 and (sat_val >= 1480 or sat_val == 0):
            category = "Target"
        elif grade_val >= 90:
            category = "Reach"
        else:
            category = "Reach"
    elif tier == 3: # Strong
        if grade_val >= 90:
            category = "Safety"
        elif grade_val >= 80:
            category = "Target"
        else:
            category = "Reach"
    else: # Standard / Tier 4
        if grade_val >= 85:
            category = "Safety"
        elif grade_val >= 70:
            category = "Target"
        else:
            category = "Reach"

    return jsonify({"category": category, "tier": tier})


@app.route("/api/exams")
@login_required
def api_exams():
    return jsonify(load_exams())

@app.route("/api/calendar/<student_id>")
@student_self_only
def api_calendar(student_id):
    student = next((s for s in STUDENTS if s["id"] == student_id), None)
    if not student:
        return jsonify({"error": "Student not found"}), 404

    events = []
    seen_event_keys = set()

    # 1. Target Course Deadlines
    for tid in student.get("targets", []):
        t = kg.get_course_or_exam(tid)
        if t:
            for dl in t.get("deadlines", []):
                key = (t["name"], dl["label"], dl["date"])
                if key not in seen_event_keys:
                    seen_event_keys.add(key)
                    events.append({
                        "title": f"{t['name']} - {dl['label']}",
                        "date": dl["date"],
                        "type": "college",
                        "description": dl.get("description", "")
                    })

    # 2. Shortlisted College Deadlines
    colleges = load_colleges()
    shortlisted_ids = student.get("shortlisted_colleges", [])
    for cid in shortlisted_ids:
        c = next((col for col in colleges if col["id"] == cid), None)
        if c:
            for dl in c.get("deadlines", []):
                key = (c["name"], dl["label"], dl["date"])
                if key not in seen_event_keys:
                    seen_event_keys.add(key)
                    events.append({
                        "title": f"{c['name']} - {dl['label']}",
                        "date": dl["date"],
                        "type": "college",
                        "description": dl.get("description", "")
                    })

    # 3. Standardized Entrance Exams Timelines
    exams = load_exams()
    student_tracks = set()
    required_exam_ids = set()

    for tid in student.get("targets", []):
        t = kg.get_course_or_exam(tid)
        if t:
            student_tracks.add(t.get("track"))
            for et in t.get("admission_tests", []):
                required_exam_ids.add(et)

    for cid in shortlisted_ids:
        c = next((col for col in colleges if col["id"] == cid), None)
        if c:
            student_tracks.add(c.get("country"))
            for ex in c.get("required_exams", []):
                required_exam_ids.add(ex)

    for ex in exams:
        is_relevant = (
            ex["id"] in required_exam_ids or 
            ex["track"] in student_tracks or
            (ex["track"] == "US" and "US" in student_tracks) or
            (ex["track"] == "UK" and "UK" in student_tracks) or
            (ex["track"] == "India" and "India" in student_tracks)
        )
        if is_relevant:
            reg_key = (ex["name"], "Registration Deadline", ex["deadline"])
            if reg_key not in seen_event_keys:
                seen_event_keys.add(reg_key)
                events.append({
                    "title": f"{ex['name']} Registration Close",
                    "date": ex["deadline"],
                    "type": "exam",
                    "description": f"Registration closes. {ex['description']}"
                })
            exam_key = (ex["name"], "Exam Date", ex["exam_date"])
            if exam_key not in seen_event_keys:
                seen_event_keys.add(exam_key)
                events.append({
                    "title": f"{ex['name']} Exam Date",
                    "date": ex["exam_date"],
                    "type": "exam",
                    "description": f"Official test date. {ex['description']}"
                })

    # 4. Competition Deadlines (Opportunity Radar - Match Score >= 75%)
    competitions = load_competitions()
    matches = OpportunityRadar.match_student(student, competitions)
    for m in matches:
        if m["match_score"] >= 75:
            comp = m["competition"]
            if comp.get("deadline"):
                key = (comp["name"], "Submission Deadline", comp["deadline"])
                if key not in seen_event_keys:
                    seen_event_keys.add(key)
                    events.append({
                        "title": f"{comp['name']} Deadline",
                        "date": comp["deadline"],
                        "type": "competition",
                        "description": comp.get("description", "")
                    })

    events.sort(key=lambda x: x["date"])
    return jsonify(events)

# ── Scholarship & Financial Aid Endpoints ──

SCHOLARSHIPS_PATH = os.path.join(BASE_DIR, "data", "scholarships.json")

def load_scholarships():
    if os.path.exists(SCHOLARSHIPS_PATH):
        with open(SCHOLARSHIPS_PATH, "r", encoding="utf-8") as f:
            return json.load(f)
    return []

def save_scholarships(schols):
    with open(SCHOLARSHIPS_PATH, "w", encoding="utf-8") as f:
        json.dump(schols, f, indent=2)

@app.route("/api/scholarships", methods=["GET"])
@login_required
def api_get_scholarships():
    return jsonify(load_scholarships())

@app.route("/api/match_scholarships/<student_id>")
@student_self_only
def api_match_scholarships(student_id):
    student = next((s for s in STUDENTS if s["id"] == student_id), None)
    if not student:
        return jsonify({"error": "Student not found"}), 404
        
    scholarships = load_scholarships()
    matches = ScholarshipAgent.match_scholarships(student, scholarships)
    return jsonify(matches)

@app.route("/api/recommend_scholarship_students/<scholarship_id>", methods=["POST"])
@counselor_required
def api_recommend_scholarship_students(scholarship_id):
    scholarships = load_scholarships()
    scholarship = next((s for s in scholarships if s["id"] == scholarship_id), None)
    if not scholarship:
        return jsonify({"error": "Scholarship not found"}), 404
    
    recommended = ScholarshipAgent.recommend_students(scholarship, STUDENTS)
    return jsonify(recommended)

@app.route("/api/students/<student_id>/shortlist_scholarship", methods=["POST"])
@counselor_required
def api_shortlist_scholarship(student_id):
    student = next((s for s in STUDENTS if s["id"] == student_id), None)
    if not student:
        return jsonify({"error": "Student not found"}), 404
    
    data = request.json
    scholarship_id = data.get("scholarship_id")
    if not scholarship_id:
        return jsonify({"error": "Missing scholarship_id"}), 400
        
    if "shortlisted_scholarships" not in student:
        student["shortlisted_scholarships"] = []
        
    if scholarship_id in student["shortlisted_scholarships"]:
        student["shortlisted_scholarships"].remove(scholarship_id)
        added = False
    else:
        student["shortlisted_scholarships"].append(scholarship_id)
        added = True
        
    save_students()
    return jsonify({"success": True, "added": added, "shortlisted": student["shortlisted_scholarships"]})

@app.route("/api/import_scholarship", methods=["POST"])
@counselor_required
def api_import_scholarship():
    data = request.get_json()
    if not data or "name" not in data:
        return jsonify({"error": "Scholarship name is required"}), 400
        
    import datetime
    schol_id = f"schol_custom_{int(datetime.datetime.now().timestamp())}"
    
    new_schol = {
        "id": schol_id,
        "name": data.get("name"),
        "type": data.get("type", "Merit-based"),
        "provider": data.get("provider", "Unknown Provider"),
        "eligibility_criteria": data.get("eligibility_criteria", "See official website for details."),
        "award_value": data.get("award_value", "Varies"),
        "deadline": data.get("deadline", "TBD"),
        "tags": data.get("tags", []),
        "min_class_level": int(data.get("min_class_level", 9)),
        "max_class_level": int(data.get("max_class_level", 12)),
        "url": data.get("url", "#")
    }
    
    schols = load_scholarships()
    schols.append(new_schol)
    save_scholarships(schols)
    
    return jsonify({"success": True, "scholarship": new_schol})

# ── Recommendation Studio ──

@app.route("/api/draft_recommendation", methods=["POST"])
@counselor_required
def api_draft_recommendation():
    data = request.get_json()
    student_id = data.get("student_id")
    student = next((s for s in STUDENTS if s["id"] == student_id), None)
    if not student:
        return jsonify({"error": "Student not found"}), 404
        
    portfolio = student.get("portfolio", [])
    grades = student.get("grades", {})
    targets = student.get("targets", [])
    
    brag_sheet = f"Student Name: {student['name']}\n"
    brag_sheet += f"Board: {student.get('board')} Class {student.get('class_level')}\n"
    brag_sheet += f"Grades: {json.dumps(grades)}\n"
    brag_sheet += "Extracurriculars & Portfolio:\n"
    for item in portfolio:
        brag_sheet += f"- {item.get('title', '')} ({item.get('role', '')}): {item.get('description', '')}\n"
    brag_sheet += f"Target Universities: {', '.join(targets)}\n"

    system_prompt = "You are an expert high school counselor writing a powerful, persuasive Letter of Recommendation (LOR) for a student's university application. Use the student's exact brag sheet and data to write a tailored draft. Do not use generic placeholders like [Name], use the real name. Keep it professional, highlighting their specific achievements. Output ONLY the letter itself."
    
    import requests
    from flask import Response
    try:
        ollama_res = requests.post("http://127.0.0.1:11434/api/generate", json={
            "model": "llama3.2",
            "prompt": f"{system_prompt}\n\nSTUDENT BRAG SHEET:\n{brag_sheet}\n\nDraft the complete Letter of Recommendation below:",
            "stream": True,
            "options": {"temperature": 0.6}
        }, timeout=60, stream=True)
        
        def generate():
            for line in ollama_res.iter_lines():
                if line:
                    try:
                        import json
                        chunk = json.loads(line.decode('utf-8'))
                        if "response" in chunk:
                            yield chunk["response"]
                    except:
                        pass
        
        return Response(generate(), mimetype='text/plain')
    except Exception as e:
        print(f"[Recommendation Error] Ollama failed: {e}")
        return jsonify({"error": "Engine failed to generate draft."}), 500

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=3000, debug=True)
