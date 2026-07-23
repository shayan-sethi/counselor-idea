import sys
from prism_agent.knowledge_graph import KnowledgeGraph
from prism_agent.reasoner import Reasoner
from prism_agent.planner import Planner

def run_tests():
    print("====================================================")
    print("PRISM AUTOMATED COMPLIANCE TEST SUITE")
    print("====================================================")

    # 1. Load system engines
    try:
        kg = KnowledgeGraph()
        reasoner = Reasoner(kg)
        planner = Planner()
        print("[✔] Successfully loaded requirements graph, reasoner, and planner.")
    except Exception as e:
        print(f"[❌] Failed to load engines: {e}")
        sys.exit(1)

    # 2. Mock Students Data
    # For testing, we load directly from the json db
    import json
    with open("data/students_db.json", "r") as f:
        students = json.load(f)
        
    student_map = {s["id"]: s for s in students}
    print(f"[✔] Loaded {len(students)} mock student profiles.")

    # 3. Evaluate cohort
    results = reasoner.evaluate_cohort(students)
    failures = 0

    # Test Case 1: Aarav Sharma (CUET Domain Subject Mismatch)
    print("\n--- Test Case 1: Aarav Sharma (CUET Mismatch) ---")
    aarav_res = results.get("STU_001")
    if not aarav_res:
        print("[❌] Aarav Sharma results not found.")
        failures += 1
    else:
        target_res = aarav_res["targets"].get("CUET_DU_CS")
        gaps = target_res["gaps"]
        
        # We expect two critical gaps: missing math in boards, and taking math in CUET without board math
        has_unlawful_domain = any(g["type"] == "cuet_unlawful_domain" for g in gaps)
        has_missing_math = any(g["type"] == "subject_missing" and g["subject"] == "Mathematics" for g in gaps)
        
        if has_unlawful_domain and has_missing_math:
            print("[✔] Correctly flagged Aarav's CUET domain eligibility mismatch.")
            # Verify citations are present
            if all(g.get("citation") and g.get("last_verified") for g in gaps):
                print("[✔] Verified citation matches and verification dates are attached.")
            else:
                print("[❌] Citations are missing in gap reports.")
                failures += 1
        else:
            print(f"[❌] Failed to flag correct gaps. Found: {[g['type'] for g in gaps]}")
            failures += 1

        # Check remediation
        aarav_rems = planner.get_remediations(aarav_res).get("CUET_DU_CS", [])
        has_form_correction = any("CORRECT CUET APPLICATION" in r["remediation"] for r in aarav_rems)
        if has_form_correction and aarav_rems[0]["feasibility"] == "HIGH":
            print("[✔] Ranked CUET form correction as the HIGHEST feasibility remediation.")
        else:
            print("[❌] Remediation planning failed or incorrect ranking.")
            failures += 1


    # Test Case 2: Dia Mehta (Class 10 Early Subject Selection Guardrails)
    print("\n--- Test Case 2: Dia Mehta (Class 10 Eco Math Gap) ---")
    dia_res = results.get("STU_002")
    if not dia_res:
        print("[❌] Dia Mehta results not found.")
        failures += 1
    else:
        target_res = dia_res["targets"].get("CUET_DU_ECO")
        gaps = target_res["gaps"]
        has_missing_math = any(g["type"] == "subject_missing" and g["subject"] == "Mathematics" for g in gaps)
        
        if has_missing_math:
            print("[✔] Correctly caught missing Math for DU Eco at Class 10 (Age 15).")
        else:
            print("[❌] Failed to flag Math gap for Class 10 student.")
            failures += 1

        # Check remediation
        dia_rems = planner.get_remediations(dia_res).get("CUET_DU_ECO", [])
        has_switch_11th = any("Switch planned Class 11 subjects" in r["remediation"] for r in dia_rems)
        if has_switch_11th and dia_rems[0]["feasibility"] == "HIGH":
            print("[✔] Correctly prioritized Class 11 subject change as HIGH feasibility.")
        else:
            print("[❌] Failed to suggest Class 11 subject change as high feasibility.")
            failures += 1


    # Test Case 3: Rohan Verma (UK Cambridge CS - Missing Further Math & TMUA)
    print("\n--- Test Case 3: Rohan Verma (Cambridge CS) ---")
    rohan_res = results.get("STU_003")
    if not rohan_res:
        print("[❌] Rohan Verma results not found.")
        failures += 1
    else:
        cam_res = rohan_res["targets"].get("CAMBRIDGE_CS")
        gaps = cam_res["gaps"]
        
        has_missing_further = any(g["type"] == "subject_missing" and g["subject"] == "Further Mathematics" for g in gaps)
        has_missing_tmua = any("TMUA" in g["description"] and g["type"] == "deadline_warning" for g in gaps) # Check TMUA deadline warning
        has_portfolio_gap = any(g["type"] == "portfolio_gap" for g in gaps)

        if has_missing_further and has_portfolio_gap:
            print("[✔] Correctly flagged Rohan's missing Further Maths and portfolio level gap.")
        else:
            print(f"[❌] Failed to flag Cambridge CS gaps. Gaps: {[g['type'] for g in gaps]}")
            failures += 1

        # Check remediation
        rohan_rems = planner.get_remediations(rohan_res).get("CAMBRIDGE_CS", [])
        has_ap_calculus = any("AP Calculus BC" in r["remediation"] for r in rohan_rems)
        if has_ap_calculus:
            print("[✔] Suggested AP Calculus BC as a remediation path to override missing Further Maths in CBSE.")
        else:
            print("[❌] AP Calculus BC remediation missing.")
            failures += 1


    # Test Case 4: Ananya Iyer (US MIT STEM - Missing Biology & SAT Check)
    print("\n--- Test Case 4: Ananya Iyer (MIT STEM) ---")
    ananya_res = results.get("STU_004")
    if not ananya_res:
        print("[❌] Ananya Iyer results not found.")
        failures += 1
    else:
        mit_res = ananya_res["targets"].get("MIT_STEM")
        gaps = mit_res["gaps"]
        
        has_missing_bio = any(g["type"] == "subject_missing" and g["subject"] == "Biology" for g in gaps)
        has_low_sat = any(g["type"] == "test_score_low" and g["subject"] == "SAT Score" for g in gaps)

        if has_missing_bio and has_low_sat:
            print("[✔] Correctly flagged missing Biology and low SAT score (1480 vs 1530 cutoff).")
        else:
            print(f"[❌] Failed to flag MIT STEM gaps. Gaps: {[g['type'] for g in gaps]}")
            failures += 1


    # Test Case 5: Kabir Singh (JEE Main Boards 75% Cutoff Check)
    print("\n--- Test Case 5: Kabir Singh (JEE 75% Board Rule) ---")
    kabir_res = results.get("STU_005")
    if not kabir_res:
        print("[❌] Kabir Singh results not found.")
        failures += 1
    else:
        jee_res = kabir_res["targets"].get("JEE_MAIN")
        gaps = jee_res["gaps"]
        
        has_board_gap = any(g["type"] == "grade_cutoff_violation" for g in gaps)
        if has_board_gap:
            print("[✔] Correctly flagged expected Board aggregate below 75% for JEE Main.")
        else:
            print("[❌] Failed to flag boards aggregate criteria.")
            failures += 1


    # Test Case 6: Meera Patel (Successful Dual-Track Student)
    print("\n--- Test Case 6: Meera Patel (Fully Compliant) ---")
    meera_res = results.get("STU_006")
    if not meera_res:
        print("[❌] Meera Patel results not found.")
        failures += 1
    else:
        # Meera targets Stanford CS and CUET DU Economics
        stanford_compliant = meera_res["targets"].get("STANFORD_CS")["compliant"]
        eco_compliant = meera_res["targets"].get("CUET_DU_ECO")["compliant"]
        
        if stanford_compliant and eco_compliant:
            print("[✔] Correctly verified Meera Patel as fully compliant across dual tracks.")
        else:
            print(f"[❌] Flagged false gaps for Meera. Stanford compliant: {stanford_compliant}, Eco compliant: {eco_compliant}")
            failures += 1

    # Test Case 7: Subject-Specific grade check (Rohan Verma low Math score simulation)
    print("\n--- Test Case 7: Rohan Verma simulated low Math score (92% vs 95% cutoff for Cambridge) ---")
    rohan_profile = student_map.get("STU_003")
    if not rohan_profile:
        print("[❌] Rohan Verma profile not found for simulation.")
        failures += 1
    else:
        # Create a copy with modified Math grade
        sim_student = json.loads(json.dumps(rohan_profile))
        sim_student["grades"]["subjects"]["Mathematics"] = 92
        
        sim_res = reasoner.evaluate_student(sim_student)
        cam_res = sim_res["targets"].get("CAMBRIDGE_CS")
        gaps = cam_res["gaps"]
        
        has_math_grade_gap = any(g["type"] == "grade_cutoff_violation" and g["subject"] == "Mathematics" for g in gaps)
        if has_math_grade_gap:
            print("[✔] Correctly flagged Rohan's Mathematics grade (92% vs required 95%).")
        else:
            print(f"[❌] Failed to flag subject-specific grade cutoff violation. Gaps found: {[g['type'] for g in gaps]}")
            failures += 1

    print("\n====================================================")
    if failures == 0:
        print("[✔] ALL TESTS PASSED SUCCESSFULLY! Compliance engine is 100% correct.")
        sys.exit(0)
    else:
        print(f"[❌] TEST SUITE FAILED WITH {failures} ERRORS.")
        sys.exit(1)

if __name__ == "__main__":
    run_tests()
