import datetime
import copy
from .knowledge_graph import KnowledgeGraph
from .board_converter import BoardGradeConverter

class Reasoner:
    def __init__(self, knowledge_graph: KnowledgeGraph, current_date_str="2026-07-22"):
        self.kg = knowledge_graph
        self.current_date = datetime.datetime.strptime(current_date_str, "%Y-%m-%d").date()

    def _get_citation(self, target, default_clause=""):
        if target.get("citations") and len(target["citations"]) > 0:
            citation = target["citations"][0]
            clause = f" ({citation['clause']})" if citation.get("clause") else f" ({default_clause})" if default_clause else ""
            return citation["source"] + clause
        return "Custom Target Profile Guidelines"

    def _get_last_verified(self, target):
        if target.get("citations") and len(target["citations"]) > 0:
            return target["citations"][0].get("last_verified", "2026-07-23")
        return "2026-07-23"

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
        student = BoardGradeConverter.standardize_profile_grades(copy.deepcopy(student))
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
            match_score = self._calculate_match_score(gaps, student, target)
            risk_level = self._risk_level_label(match_score)

            student_results["targets"][target_id] = {
                "target_name": target["name"],
                "track": target["track"],
                "compliant": len(gaps) == 0,
                "match_score": match_score,
                "risk_level": risk_level,
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
                        "citation": self._get_citation(target, req.get("clause", "")),
                        "last_verified": self._get_last_verified(target)
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
                        "citation": self._get_citation(target, req.get("clause", "")),
                        "last_verified": self._get_last_verified(target)
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
                                "citation": self._get_citation(target, req.get("clause", "")),
                                "last_verified": self._get_last_verified(target)
                            })
                    else:
                        gaps.append({
                            "type": "subject_missing",
                            "severity": "CRITICAL" if req_level == "compulsory" else "WARNING",
                            "subject": req_subject,
                            "description": f"Missing compulsory subject '{req_subject}' in high school curriculum. {notes}",
                            "citation": self._get_citation(target, req.get("clause", "")),
                            "last_verified": self._get_last_verified(target)
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
                    "citation": self._get_citation(target, "Section 1(a)"),
                    "last_verified": self._get_last_verified(target)
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
                    "citation": self._get_citation(target, "Undergraduate Common Eligibility Guidelines"),
                    "last_verified": self._get_last_verified(target)
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
                                "citation": self._get_citation(target, req.get("clause", "")),
                                "last_verified": self._get_last_verified(target)
                            })
                    
                    # Check individual subject grades if present in student's profile
                    student_subjects_grades = grades_data.get("subjects", {})
                    if student_subjects_grades:
                        import re
                        # Find all patterns like "95% in Mathematics"
                        matches = re.findall(r'(\d+(?:\.\d+)?)\%\s+in\s+([A-Za-z\s&,]+)', notes)
                        for pct_str, subj_name in matches:
                            clean_subj = re.sub(r'[^\w\s]', '', subj_name).strip().lower()
                            # Ignore patterns matching overall aggregate phrases
                            if any(ignored in clean_subj for ignored in ["top 5", "board", "class", "aggregate"]):
                                continue
                            required_mark = float(pct_str)
                            for s_name, s_grade in student_subjects_grades.items():
                                if clean_subj in s_name.lower() or s_name.lower() in clean_subj:
                                    try:
                                        grade_val = float(s_grade)
                                        # Only warn if the grade is valid (> 0)
                                        if grade_val > 0 and grade_val < required_mark:
                                            gaps.append({
                                                "type": "grade_cutoff_violation",
                                                "severity": "CRITICAL" if target["track"] == "India" else "WARNING",
                                                "subject": s_name,
                                                "description": f"Expected {s_name} score ({grade_val}%) is below the required subject cutoff of {pct_str}%. {notes}",
                                                "citation": self._get_citation(target, req.get("clause", "")),
                                                "last_verified": self._get_last_verified(target)
                                            })
                                    except ValueError:
                                        pass
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
                                "citation": self._get_citation(target, req.get("clause", "")),
                                "last_verified": self._get_last_verified(target)
                            })
                    elif target["track"] == "US":
                        # MIT requires SAT. Stanford requires SAT.
                        gaps.append({
                            "type": "test_missing",
                            "severity": "CRITICAL",
                            "subject": "SAT Exam",
                            "description": f"SAT is compulsory but student profile has no registered SAT score. {notes}",
                            "citation": self._get_citation(target, req.get("clause", "")),
                            "last_verified": self._get_last_verified(target)
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
                    "citation": self._get_citation(target, "Timeline announcements"),
                    "last_verified": self._get_last_verified(target)
                })
            elif days_remaining <= 2: # 48 hours
                gaps.append({
                    "type": "deadline_critical",
                    "severity": "CRITICAL",
                    "subject": label,
                    "description": f"CRITICAL: '{label}' closes in {days_remaining} days (on {dl['date']})! Urgent action required.",
                    "citation": self._get_citation(target, "Timeline announcements"),
                    "last_verified": self._get_last_verified(target)
                })
            elif days_remaining <= 14: # 2 weeks warning
                gaps.append({
                    "type": "deadline_warning",
                    "severity": "WARNING",
                    "subject": label,
                    "description": f"WARNING: '{label}' is approaching in {days_remaining} days ({dl['date']}).",
                    "citation": self._get_citation(target, "Timeline announcements"),
                    "last_verified": self._get_last_verified(target)
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
                "citation": self._get_citation(target, "Holistic Review Process / Portfolio Guidelines"),
                "last_verified": self._get_last_verified(target)
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

    def _calculate_match_score(self, gaps, student=None, target=None):
        """
        Calculates a realistic 0-100 match score using a weighted composite model:

          Score = (0.40 × S_prereq) + (0.35 × S_academic) + (0.25 × S_profile) − P_penalties

        Hard gate: if any mandatory prerequisite is missing, S_prereq = 0 and the
        total score is capped at 35 regardless of academic or profile strength.

        An institutional selectivity ceiling is applied after composition:
          - Super-selective (Tier-1 portfolio target / elite US/UK): max 78
          - Highly competitive (Tier-2 portfolio target):            max 85
          - Moderate (Tier-3 portfolio target):                      max 92

        A deadline proximity penalty of up to 15 points is subtracted before
        the ceiling is applied when critical deadlines are missed or expiring.
        """
        # ── Component 1: Prerequisite gate (40% weight) ───────────────────────
        s_prereq, hard_cap = self._score_prereq_component(gaps)

        # ── Component 2: Academic / exam fit (35% weight) ────────────────────
        s_academic = self._score_academic_component(student, target, gaps)

        # ── Component 3: Portfolio / profile depth (25% weight) ──────────────
        s_profile = self._score_profile_component(student)

        # ── Weighted composite ───────────────────────────────────────────────
        raw_score = (0.40 * s_prereq) + (0.35 * s_academic) + (0.25 * s_profile)

        # ── Hard gate cap: missing mandatory prereq → max 35 ─────────────────
        if hard_cap:
            score = min(raw_score, 35.0)
            return int(round(score))

        # ── Deadline proximity penalty ────────────────────────────────────────
        score = self._apply_deadline_penalty(raw_score, gaps)

        # ── Institutional selectivity ceiling ─────────────────────────────────
        score = self._apply_institutional_ceiling(score, target)

        return int(round(max(5, score)))

    # ── Scoring sub-component helpers ─────────────────────────────────────────

    @staticmethod
    def _score_prereq_component(gaps):
        """
        Returns (S_prereq, hard_cap_triggered).

        S_prereq is 100 if ALL mandatory prerequisites are satisfied.
        S_prereq is 0 and hard_cap_triggered is True if ANY gap of type
        'subject_missing', 'cuet_missing_subject', or 'cuet_unlawful_domain'
        with severity CRITICAL exists — these represent structural eligibility
        blockers that no amount of grades or extracurriculars can overcome.
        """
        HARD_BLOCK_TYPES = {"subject_missing", "cuet_missing_subject", "cuet_unlawful_domain"}
        for gap in gaps:
            if gap.get("type") in HARD_BLOCK_TYPES and gap.get("severity") == "CRITICAL":
                return 0.0, True   # Hard gate triggered — cap total at 35
        return 100.0, False

    @staticmethod
    def _score_academic_component(student, target, gaps):
        """
        Returns S_academic in [20, 92] based on how the student's expected
        grade compares to the target's stated minimum cutoff.

        Scoring bands (mimicking a realistic percentile distribution):
          - Expected grade >= min_grade (at or above cutoff):        80 – 92
          - Within 10 percentage points below cutoff (25th–75th):   50 – 79
          - More than 10 percentage points below cutoff (< 25th):   20 – 49

        If a test_score_low or grade_cutoff_violation gap is present,
        the score is additionally penalised by 8–15 points within its band.
        Capped at 92 to account for exam-day variance and measurement error.
        """
        base = 65.0  # Default mid-range when no data is available

        if student and target:
            grades_data = student.get("grades", {})
            exp_str = grades_data.get("current_expected_board", "")
            student_board = student.get("board", "CBSE")

            # Find the numeric minimum grade for the student's board system
            min_grade_val = None
            for req in target.get("grade_prerequisites", []):
                if req.get("system") == student_board:
                    try:
                        min_grade_val = float(
                            str(req["min_grade"]).replace("%", "").strip()
                        )
                    except (ValueError, KeyError):
                        pass
                    break

            # Parse expected grade to a float percentage
            exp_val = None
            if exp_str:
                try:
                    exp_val = float(str(exp_str).replace("%", "").strip())
                    # Sanity-clamp IB total-points style values (e.g. "33/45" already
                    # converted to % by BoardGradeConverter before this call)
                    if exp_val > 100:
                        exp_val = min(exp_val, 100.0)
                except ValueError:
                    pass

            if exp_val is not None and min_grade_val is not None:
                gap_from_cutoff = exp_val - min_grade_val  # positive = above cutoff

                if gap_from_cutoff >= 0:
                    # At or above cutoff: 80–92 scaled by how far above
                    # Every 1% above cutoff adds ~0.4 pts, hard-capped at 92
                    base = min(92.0, 80.0 + gap_from_cutoff * 0.4)
                elif gap_from_cutoff >= -10:
                    # Within 10 pts below cutoff: 50–79
                    # -10 → 50, 0 → 79
                    base = 50.0 + (gap_from_cutoff + 10) * 2.9
                else:
                    # More than 10 pts below cutoff: 20–49
                    # -10 → 49, -40 (extreme) → 20
                    below = abs(gap_from_cutoff) - 10  # extra deficit beyond -10
                    base = max(20.0, 49.0 - below * 0.97)
            elif exp_val is not None:
                # No specific min grade found — use absolute performance bands
                if exp_val >= 92:
                    base = 82.0
                elif exp_val >= 80:
                    base = 67.0
                elif exp_val >= 65:
                    base = 52.0
                else:
                    base = 35.0

        # Apply penalty for grade/test-score violations already flagged as gaps
        ACADEMIC_PENALTY_TYPES = {"grade_cutoff_violation", "test_score_low", "test_missing"}
        for gap in gaps:
            if gap.get("type") in ACADEMIC_PENALTY_TYPES:
                sev = gap.get("severity", "WARNING")
                base -= 15 if sev == "CRITICAL" else 8

        return max(20.0, min(92.0, base))

    @staticmethod
    def _score_profile_component(student):
        """
        Returns S_profile in [30, 88] based on the student's extracurricular
        portfolio tier.

        Scoring:
          - Tier 1 (international / national Olympiad / published research): 78–88
          - Tier 2 (state / regional / major club president / hackathon):    55–70
          - Tier 3 (basic school activities):                                 38–52
          - No portfolio at all:                                               30

        Multiple Tier-1 or Tier-2 activities add a small bonus (capped).
        """
        portfolio = student.get("portfolio", []) if student else []
        if not portfolio:
            return 30.0

        tiers = [act.get("tier", 3) for act in portfolio]
        best_tier = min(tiers)  # lower tier number = better
        count_t1 = tiers.count(1)
        count_t2 = tiers.count(2)

        if best_tier == 1:
            # Base 78; +2 per additional Tier-1 activity, capped at 88
            return min(88.0, 78.0 + max(0, count_t1 - 1) * 2.0)
        elif best_tier == 2:
            # Base 55; +5 for each Tier-2 beyond the first, capped at 70
            return min(70.0, 55.0 + max(0, count_t2 - 1) * 5.0)
        else:
            # Tier 3 only
            return 38.0 + min(14.0, len(portfolio) * 2.0)  # small depth bonus

    @staticmethod
    def _apply_institutional_ceiling(score, target):
        """
        Applies an acceptance-rate-based ceiling to the composite score.

        Super-selective targets (portfolio_tier == 1 or named elite institutions)
        represent <10% acceptance rate environments; no matter how strong a profile
        looks on paper, the competition means a realistic maximum is ~78%.

        Tiers:
          - Super-selective (portfolio_tier 1 / elite name):  max 78
          - Highly competitive (portfolio_tier 2):             max 85
          - Moderate (portfolio_tier 3):                       max 92
        """
        if not target:
            return score

        ELITE_KEYWORDS = [
            "cambridge", "oxford", "mit", "stanford", "harvard",
            "yale", "princeton", "caltech", "imperial", "iit", "aiims"
        ]
        uni_name = (target.get("university", "") or target.get("name", "")).lower()
        portfolio_tier = int(target.get("portfolio_tier", 3))

        is_super_selective = portfolio_tier == 1 or any(
            kw in uni_name for kw in ELITE_KEYWORDS
        )

        if is_super_selective:
            return min(score, 78.0)
        elif portfolio_tier == 2:
            return min(score, 85.0)
        else:
            return min(score, 92.0)

    @staticmethod
    def _apply_deadline_penalty(score, gaps):
        """
        Subtracts up to 15 points when critical deadlines have expired or are
        closing within 48 hours without prerequisite actions completed.

          - deadline_expired:  −15 pts (irreversible — door is closed)
          - deadline_critical: −8 pts  (closing imminently)
          - deadline_warning:  −3 pts  (approaching)
        """
        PENALTY_MAP = {
            "deadline_expired": 15,
            "deadline_critical": 8,
            "deadline_warning": 3,
        }
        total_penalty = 0
        for gap in gaps:
            total_penalty += PENALTY_MAP.get(gap.get("type", ""), 0)
        # Cap total deadline penalty at 15 to avoid double-counting multiple deadlines
        return score - min(total_penalty, 15)

    @staticmethod
    def _risk_level_label(match_score):
        """
        Maps a realistic match score to a human-readable risk label.

        With the new composite model, scores are distributed across a realistic
        bell curve (mean ~55-68%). Labels are calibrated accordingly:
          > 85  — Exceptional Match (rare; top-decile academics + Tier-1 portfolio)
          70–85 — Strong Match
          40–69 — Moderate / Work Needed
          < 40  — Critical / High Risk
        """
        if match_score >= 85:
            return "Exceptional Match"
        elif match_score >= 70:
            return "Strong Match"
        elif match_score >= 40:
            return "Moderate Risk"
        else:
            return "Critical"

    def _classify_difficulty(self, student, target, match_score, gaps):
        """
        Classifies the target difficulty into Reach, Target, or Safety.

        Thresholds are calibrated for the new realistic scoring distribution
        (mean ≈ 55–68%; ceiling ≤ 92%):

          Reach:  Any critical gap OR match_score < 55
          Safety: match_score >= 75 AND no critical gaps AND student meets
                  portfolio tier AND target is not elite/super-selective
          Target: everything in between
        """
        SUPER_SELECTIVE = [
            "cambridge", "oxford", "mit", "stanford", "harvard",
            "yale", "princeton", "caltech", "imperial", "iit bombay",
            "iit delhi", "iit madras", "aiims", "columbia", "chicago",
            "berkeley", "cornell", "pennsylvania"
        ]

        uni_name = (target.get("university", "") or target.get("name", "")).lower()
        is_super_selective = any(kw in uni_name for kw in SUPER_SELECTIVE)

        has_critical_gaps = any(gap.get("severity") == "CRITICAL" for gap in gaps)

        # Any hard blocker or weak match → Reach
        if has_critical_gaps or match_score < 55:
            return "Reach"

        # Super-selective institutions are always at least a Target, never Safety
        if is_super_selective:
            if match_score >= 72:
                return "Target"
            return "Reach"

        # Check if student's portfolio matches the required tier for Safety classification
        portfolio = student.get("portfolio", []) if student else []
        student_best_tier = min([act.get("tier", 3) for act in portfolio]) if portfolio else 4
        req_portfolio_tier = int(target.get("portfolio_tier", 3))

        if match_score >= 75 and student_best_tier <= req_portfolio_tier:
            return "Safety"

        return "Target"
