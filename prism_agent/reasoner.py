import datetime
from .knowledge_graph import KnowledgeGraph

class Reasoner:
    def __init__(self, knowledge_graph: KnowledgeGraph, current_date_str="2026-07-22"):
        self.kg = knowledge_graph
        self.current_date = datetime.datetime.strptime(current_date_str, "%Y-%m-%d").date()

    def evaluate_cohort(self, students):
        """Evaluates compliance for a cohort of students."""
        cohort_results = {}
        for student in students:
            cohort_results[student["id"]] = self.evaluate_student(student)
        return cohort_results

    def evaluate_student(self, student, simulated_subjects=None):
        """
        Evaluates compliance for a single student against all their target courses/exams.
        Allows overriding board subjects for hypothetical simulation.
        """
        targets = student.get("targets", [])
        student_results = {
            "student_id": student["id"],
            "student_name": student["name"],
            "class_level": student["class_level"],
            "targets": {}
        }

        # Use simulated subjects if provided (for pivot simulation)
        if simulated_subjects is not None:
            board_subjects = simulated_subjects
        elif student.get("class_level") == 10 and student.get("planned_class_11_subjects"):
            board_subjects = student.get("planned_class_11_subjects")
        else:
            board_subjects = student.get("board_subjects", [])
        # Normalise subject names to lowercase to prevent matching errors
        norm_board_subjects = [s.lower().strip() for s in board_subjects]

        for target_id in targets:
            target = self.kg.get_course_or_exam(target_id)
            if not target:
                continue

            gaps = []
            
            # 1. Subject Prerequisite Checks
            self._check_subject_prerequisites(target, norm_board_subjects, student, gaps)

            # 2. CUET Domain Mapping Checks (DU / India specific compliance rules)
            if target.get("track") == "India" and "CUET_UG" in target.get("admission_tests", []):
                self._check_cuet_domain_alignment(target, norm_board_subjects, student, gaps)

            # 3. Grade / Test score Prerequisite Checks
            self._check_grade_prerequisites(target, student, gaps)

            # 4. Deadline / Timeline Checks
            self._check_deadlines(target, gaps)

            # 5. Portfolio / Extracurricular Tier Checks
            self._check_portfolio_tier(target, student, gaps)

            # Calculate overall target urgency score (risk priority)
            urgency_score = self._calculate_urgency(gaps)

            student_results["targets"][target_id] = {
                "target_name": target["name"],
                "track": target["track"],
                "compliant": len(gaps) == 0,
                "urgency_score": urgency_score,
                "gaps": gaps
            }

        return student_results

    def _check_subject_prerequisites(self, target, norm_board_subjects, student, gaps):
        """Checks if board subjects meet target prerequisites."""
        prereqs = target.get("subject_prerequisites", [])
        class_level = student.get("class_level", 12)
        
        # Check if they are Class 10 (choosing subjects) or Class 11/12
        subjects_label = "planned subjects" if class_level == 10 else "subjects"
        
        # Helper to match math variations
        def has_math(subjects):
            math_keywords = ["mathematics", "math", "applied mathematics", "mathematics standard", "core mathematics"]
            return any(k in s for s in subjects for k in math_keywords)

        for req in prereqs:
            req_subject = req["subject"]
            req_level = req["level"]
            notes = req["notes"]

            # General checks
            if req_subject.lower() == "mathematics":
                if not has_math(norm_board_subjects):
                    gaps.append({
                        "type": "subject_missing",
                        "severity": "CRITICAL" if req_level == "compulsory" else "WARNING",
                        "subject": req_subject,
                        "description": f"Missing {req_subject} in board {subjects_label}. {notes}",
                        "citation": target["citations"][0]["source"] + f" ({target['citations'][0]['clause']})",
                        "last_verified": target["citations"][0]["last_verified"]
                    })
            elif req_subject.lower() == "further mathematics":
                # Special rule for foreign/UK programs
                has_further = any("further" in s and "math" in s for s in norm_board_subjects)
                # For CBSE, there's no Further Mathematics, so AP Calculus or high math aggregate is an alternative
                ap_calculus_score = student.get("standardized_tests", {}).get("AP_CALCULUS_BC", 0)
                if not has_further and ap_calculus_score < 4 and student.get("board") == "CBSE":
                    severity = "CRITICAL" if req_level == "compulsory" else "WARNING"
                    gaps.append({
                        "type": "subject_missing",
                        "severity": severity,
                        "subject": req_subject,
                        "description": f"Missing Further Mathematics or equivalent AP Calculus BC (Score >= 4) for CBSE student. {notes}",
                        "citation": target["citations"][0]["source"] + f" ({target['citations'][0]['clause']})",
                        "last_verified": target["citations"][0]["last_verified"]
                    })
            elif req_subject.lower() not in ["cuet_language", "cuet_domain_subjects"]:
                # Normal subjects like Physics, Chemistry, Biology, English
                if req_subject.lower() == "science":
                    science_keywords = ["physics", "chemistry", "biology", "science", "environmental"]
                    matching = any(any(key in s for key in science_keywords) for s in norm_board_subjects)
                else:
                    matching = [s for s in norm_board_subjects if req_subject.lower() in s]
                
                if not matching:
                    # Optional group checks (e.g. Chemistry optional group in JEE Main)
                    if req_level == "optional_group":
                        # For JEE Main: Chemistry, Bio, Biotech, Voc. Check if any are in subjects
                        optional_subjects = ["chemistry", "biotechnology", "biology", "vocational", "computer science", "information practices"]
                        has_optional = any(opt in s for s in norm_board_subjects for opt in optional_subjects)
                        if not has_optional:
                            gaps.append({
                                "type": "subject_missing",
                                "severity": "CRITICAL",
                                "subject": req_subject,
                                "description": f"Missing optional group subject. Must have studied Chemistry, Biotechnology, Biology, or a Vocational Subject. {notes}",
                                "citation": target["citations"][0]["source"] + f" ({target['citations'][0]['clause']})",
                                "last_verified": target["citations"][0]["last_verified"]
                            })
                    else:
                        gaps.append({
                            "type": "subject_missing",
                            "severity": "CRITICAL" if req_level == "compulsory" else "WARNING",
                            "subject": req_subject,
                            "description": f"Missing compulsory subject '{req_subject}' in high school curriculum. {notes}",
                            "citation": target["citations"][0]["source"] + f" ({target['citations'][0]['clause']})",
                            "last_verified": target["citations"][0]["last_verified"]
                        })

    def _check_cuet_domain_alignment(self, target, norm_board_subjects, student, gaps):
        """
        Validates CUET domain registrations against CBSE Board subjects.
        Crucial DU rule: Cannot write CUET domain exam in a subject not studied in Class 12 boards.
        """
        cuet_subjects = student.get("cuet_subjects", [])
        class_level = student.get("class_level", 12)

        if class_level < 12:
            return  # CUET exam selections apply only for Class 12

        norm_cuet = [s.lower().strip() for s in cuet_subjects]
        
        # Prerequisite lists
        has_math_in_cuet = any("math" in s for s in norm_cuet)
        has_math_in_boards = any("math" in s for s in norm_board_subjects)

        # DU Computer Science/Eco requires Math in both boards and CUET
        if target["id"] in ["CUET_DU_CS", "CUET_DU_ECO"]:
            if not has_math_in_cuet:
                gaps.append({
                    "type": "cuet_missing_subject",
                    "severity": "CRITICAL",
                    "subject": "Mathematics",
                    "description": "Mathematics is not selected in CUET, which is a compulsory test paper for DU B.Sc CS / B.A Economics.",
                    "citation": target["citations"][0]["source"] + f" ({target['citations'][0]['clause']})",
                    "last_verified": target["citations"][0]["last_verified"]
                })

        # Check for alignment: any domain exam in CUET must be in board subjects
        # We ignore generic language papers or General Test in CUET
        exempt_exams = ["english", "general test", "hindi", "language"]
        for cuet_sub in cuet_subjects:
            clean_cuet = cuet_sub.lower().strip()
            if any(exempt in clean_cuet for exempt in exempt_exams):
                continue
            
            # Map CUET subject name variations to board subject names
            # e.g., "mathematics" in CUET matches "mathematics standard" or "applied mathematics" in boards
            found = False
            for board_sub in norm_board_subjects:
                if clean_cuet in board_sub or board_sub in clean_cuet:
                    found = True
                    break
            
            if not found:
                gaps.append({
                    "type": "cuet_unlawful_domain",
                    "severity": "CRITICAL",
                    "subject": cuet_sub,
                    "description": f"CUET test paper '{cuet_sub}' does not match any studied Class 12 Board subject. Delhi University rules state you can only take CUET domain exams in subjects you studied and passed in Class 12 Boards.",
                    "citation": target["citations"][0]["source"] + f" (Undergraduate Common Eligibility Guidelines)",
                    "last_verified": target["citations"][0]["last_verified"]
                })

    def _check_grade_prerequisites(self, target, student, gaps):
        """Checks if grades or test scores violate cutoffs."""
        grade_reqs = target.get("grade_prerequisites", [])
        grades_data = student.get("grades", {})
        tests_data = student.get("standardized_tests", {})
        student_board = student.get("board")

        for req in grade_reqs:
            system = req["system"]
            min_grade_str = req["min_grade"]
            notes = req["notes"]

            # Only evaluate if the grade requirement matches the student's high school board system
            if system == student_board:
                try:
                    min_val = float(min_grade_str.replace("%", "").strip())
                    exp_grade_str = grades_data.get("current_expected_board")
                    if exp_grade_str:
                        exp_val = float(exp_grade_str.replace("%", "").strip())
                        if exp_val < min_val:
                            gaps.append({
                                "type": "grade_cutoff_violation",
                                "severity": "CRITICAL" if target["track"] == "India" else "WARNING", # UK/US is warning because board exams haven't happened yet
                                "subject": f"{student_board} Boards Aggregate",
                                "description": f"Expected Class 12 Boards aggregate ({exp_grade_str}) is below the required cutoff of {min_grade_str}. {notes}",
                                "citation": target["citations"][0]["source"] + f" ({target['citations'][0]['clause']})",
                                "last_verified": target["citations"][0]["last_verified"]
                            })
                except ValueError:
                    # Non-numeric board requirement (e.g. A*A*A under A-Level which doesn't apply directly to CBSE float grades)
                    pass
            elif system == "SAT":
                try:
                    min_val = float(min_grade_str)
                    sat_score = tests_data.get("SAT")
                    if sat_score:
                        if sat_score < min_val:
                            gaps.append({
                                "type": "test_score_low",
                                "severity": "WARNING",
                                "subject": "SAT Score",
                                "description": f"SAT score ({sat_score}) is below the target score of {min_val}. {notes}",
                                "citation": target["citations"][0]["source"] + f" ({target['citations'][0]['clause']})",
                                "last_verified": target["citations"][0]["last_verified"]
                            })
                    elif target["track"] == "US":
                        # MIT requires SAT. Stanford requires SAT.
                        gaps.append({
                            "type": "test_missing",
                            "severity": "CRITICAL",
                            "subject": "SAT Exam",
                            "description": f"SAT is compulsory but student profile has no registered SAT score. {notes}",
                            "citation": target["citations"][0]["source"] + f" ({target['citations'][0]['clause']})",
                            "last_verified": target["citations"][0]["last_verified"]
                        })
                except ValueError:
                    pass


    def _check_deadlines(self, target, gaps):
        """Evaluates deadline proximity to create risk warnings."""
        deadlines = target.get("deadlines", [])
        
        for dl in deadlines:
            dl_date = datetime.datetime.strptime(dl["date"], "%Y-%m-%d").date()
            days_remaining = (dl_date - self.current_date).days
            label = dl["label"]
            desc = dl["description"]

            if days_remaining < 0:
                gaps.append({
                    "type": "deadline_expired",
                    "severity": "CRITICAL" if dl.get("is_correction_window") else "WARNING",
                    "subject": label,
                    "description": f"The deadline for '{label}' has passed ({abs(days_remaining)} days ago on {dl['date']}). {desc}",
                    "citation": target["citations"][0]["source"] + f" (Timeline announcements)",
                    "last_verified": target["citations"][0]["last_verified"]
                })
            elif days_remaining <= 2: # 48 hours
                gaps.append({
                    "type": "deadline_critical",
                    "severity": "CRITICAL",
                    "subject": label,
                    "description": f"CRITICAL: '{label}' closes in {days_remaining} days (on {dl['date']})! Urgent action required.",
                    "citation": target["citations"][0]["source"] + f" (Timeline announcements)",
                    "last_verified": target["citations"][0]["last_verified"]
                })
            elif days_remaining <= 14: # 2 weeks warning
                gaps.append({
                    "type": "deadline_warning",
                    "severity": "WARNING",
                    "subject": label,
                    "description": f"WARNING: '{label}' is approaching in {days_remaining} days ({dl['date']}).",
                    "citation": target["citations"][0]["source"] + f" (Timeline announcements)",
                    "last_verified": target["citations"][0]["last_verified"]
                })

    def _check_portfolio_tier(self, target, student, gaps):
        """Checks if student's extracurricular achievements match university expectations."""
        target_tier = target.get("portfolio_tier", 3)
        portfolio = student.get("portfolio", [])
        
        # Find highest tier achievement (1 is best, 3 is basic, infinity if none)
        student_best_tier = 3
        if portfolio:
            student_best_tier = min([act.get("tier", 3) for act in portfolio])
        else:
            student_best_tier = 4 # No portfolio

        if student_best_tier > target_tier:
            severity = "WARNING"
            if target_tier == 1:
                desc = "Portfolio Gap: Highly selective US/UK programs expect Tier 1 achievements (e.g. patents, international Olympiads, major research publications). The student's highest extracurricular tier is Tier " + str(student_best_tier) + "."
            else:
                desc = "Portfolio Gap: Selected program recommends Tier 2 achievements (e.g. state leadership, major club founder). The student's highest extracurricular tier is Tier " + str(student_best_tier) + "."

            gaps.append({
                "type": "portfolio_gap",
                "severity": severity,
                "subject": "Extracurricular Portfolio",
                "description": desc,
                "citation": target["citations"][0]["source"] + " (Holistic Review Process / Portfolio Guidelines)",
                "last_verified": target["citations"][0]["last_verified"]
            })

    def _calculate_urgency(self, gaps):
        """Calculates a numerical risk score (0 to 100) based on severity of gaps."""
        if not gaps:
            return 0
        
        score = 0
        for gap in gaps:
            gtype = gap["type"]
            gsev = gap["severity"]
            
            if gsev == "CRITICAL":
                if "deadline" in gtype or "expired" in gtype:
                    score += 50 # Expired or highly urgent deadlines
                else:
                    score += 35 # Mandatory prerequisites missing
            elif gsev == "WARNING":
                score += 15
        
        return min(score, 100)
