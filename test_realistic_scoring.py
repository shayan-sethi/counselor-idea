import json, os, sys, copy, hashlib

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, BASE_DIR)

from prism_agent.knowledge_graph import KnowledgeGraph
from prism_agent.reasoner import Reasoner
from prism_agent.board_converter import BoardGradeConverter

kg = KnowledgeGraph()
reasoner = Reasoner(kg, current_date_str="2026-08-03")

with open(os.path.join(BASE_DIR, "data", "students_db.json"), "r", encoding="utf-8") as f:
    all_students = json.load(f)

def old_score(student_id, target_id, gaps):
    seed_str = student_id + "_" + target_id
    hash_val = int(hashlib.md5(seed_str.encode()).hexdigest(), 16)
    base = 92 + (hash_val % 7)
    deduction = 0
    for gap in gaps:
        gtype = gap.get("type", "")
        gsev = gap.get("severity", "WARNING")
        if gtype == "portfolio_gap":
            deduction += 6
        elif gsev == "CRITICAL":
            deduction += 30 if ("deadline" in gtype or "expired" in gtype) else 22
        elif gsev == "WARNING":
            deduction += 10
    return max(5, base - deduction)

SEP = "-" * 95
print(SEP)
print("  PRISM AI - Realistic Match Score Verification  |  2026-08-03")
print(SEP)
print("  {:<22} {:<38} {:>5} {:>5}  {:<22} {}".format("STUDENT","TARGET","OLD","NEW","RISK LABEL","CAP REASON"))
print(SEP)

results = []
violations = []
buckets = {"<40":0,"40-54":0,"55-69":0,"70-84":0,"85+":0}
HARD = {"subject_missing","cuet_missing_subject","cuet_unlawful_domain"}

for student in all_students:
    targets = student.get("targets", [])
    if not targets:
        continue
    std_s = BoardGradeConverter.standardize_profile_grades(copy.deepcopy(student))
    for tid in targets:
        target = kg.get_course_or_exam(tid)
        if not target:
            continue
        gaps = []
        board_subjs = std_s.get("board_subjects", [])
        if std_s.get("class_level") == 10 and std_s.get("planned_class_11_subjects"):
            board_subjs = std_s.get("planned_class_11_subjects")
        norm = [s.lower().strip() for s in board_subjs]
        reasoner._check_subject_prerequisites(target, norm, std_s, gaps)
        if target.get("track") == "India" and "CUET_UG" in target.get("admission_tests", []):
            reasoner._check_cuet_domain_alignment(target, norm, std_s, gaps)
        reasoner._check_grade_prerequisites(target, std_s, gaps)
        reasoner._check_deadlines(target, gaps)
        reasoner._check_portfolio_tier(target, std_s, gaps)
        o = old_score(student["id"], tid, gaps)
        n = reasoner._calculate_match_score(gaps, std_s, target)
        risk = reasoner._risk_level_label(n)
        mp = [g for g in gaps if g.get("type") in HARD and g.get("severity") == "CRITICAL"]
        if mp:
            cap = "Hard gate: " + mp[0].get("subject", "prereq")
        elif n <= 78 and int(target.get("portfolio_tier", 3)) == 1:
            cap = "Ceiling: super-selective (<=78)"
        elif n <= 85 and int(target.get("portfolio_tier", 3)) == 2:
            cap = "Ceiling: competitive (<=85)"
        else:
            cap = ""
        name_t = student["name"][:20]
        tid_t = tid[:37]
        print("  {:<22} {:<38} {:>5} {:>5}  {:<22} {}".format(name_t, tid_t, o, n, risk, cap))
        results.append({"old":o,"new":n,"mp":bool(mp),"cap":cap})
        if mp and n > 35:
            violations.append({"s":student["name"],"t":tid,"sc":n})
        if n < 40: buckets["<40"] += 1
        elif n < 55: buckets["40-54"] += 1
        elif n < 70: buckets["55-69"] += 1
        elif n < 85: buckets["70-84"] += 1
        else: buckets["85+"] += 1

total = len(results)
old_avg = sum(r["old"] for r in results)/total if total else 0
new_avg = sum(r["new"] for r in results)/total if total else 0
print(SEP)
print("  SUMMARY  ({} pairs)  |  OLD avg: {:.1f}%  |  NEW avg: {:.1f}%".format(total, old_avg, new_avg))
old_ge90 = sum(1 for r in results if r["old"] >= 90)
new_ge90 = sum(1 for r in results if r["new"] >= 90)
old_lt40 = sum(1 for r in results if r["old"] < 40)
new_lt40 = sum(1 for r in results if r["new"] < 40)
print("  OLD >=90%: {:3d}   NEW >=90%: {:3d}".format(old_ge90, new_ge90))
print("  OLD  <40%: {:3d}   NEW  <40%: {:3d}".format(old_lt40, new_lt40))
print(SEP)
print("  SCORE DISTRIBUTION (NEW):")
BAR = 40
for label, count in buckets.items():
    bar = "#" * int(BAR * count / max(total, 1))
    pct = 100.0 * count / total if total else 0
    print("  {:<8} {:<{}} {:>3} ({:.1f}%)".format(label, bar, BAR, count, pct))
print(SEP)
if not violations:
    print("  HARD GATE: PASSED - No prereq-missing student scored >35%")
else:
    print("  HARD GATE: FAILED - {} violation(s):".format(len(violations)))
    for v in violations:
        print("    {} -> {}: {}%".format(v["s"], v["t"], v["sc"]))
    sys.exit(1)
print(SEP)
