class Planner:
    def __init__(self, current_date_str="2026-07-22"):
        self.current_date_str = current_date_str

    def get_remediations(self, student_analysis):
        """
        Generates remediation plans for all target gaps.
        Returns a dict of target_id -> list of ranked remediation paths.
        """
        student_id = student_analysis["student_id"]
        class_level = student_analysis["class_level"]
        targets_report = student_analysis["targets"]
        
        remediations_map = {}

        for target_id, report in targets_report.items():
            if report["compliant"]:
                remediations_map[target_id] = []
                continue

            gaps = report["gaps"]
            ranked_paths = []

            for gap in gaps:
                gap_type = gap["type"]
                subject = gap.get("subject")
                desc = gap["description"]

                # Generate remediation options based on type and student context
                options = self._generate_options_for_gap(gap_type, subject, class_level)
                
                # Attach to ranked paths
                for opt in options:
                    ranked_paths.append(opt)

            # Sort remediations: High feasibility first, then Medium, then Low
            feasibility_order = {"HIGH": 3, "MEDIUM": 2, "LOW": 1}
            ranked_paths.sort(key=lambda x: feasibility_order.get(x["feasibility"], 0), reverse=True)

            remediations_map[target_id] = ranked_paths

        return remediations_map

    def _generate_options_for_gap(self, gap_type, subject, class_level):
        options = []

        if gap_type == "subject_missing":
            if subject == "Mathematics":
                if class_level <= 10:
                    options.append({
                        "remediation": "Switch planned Class 11 subjects to include Core Mathematics (Subject Code 041) or Applied Mathematics (Subject Code 241).",
                        "feasibility": "HIGH",
                        "action_item": "Counsellor to coordinate with student and school admin to update subject registration sheet prior to Class 11 session.",
                        "reasoning": "Since student is age 15 (Class 10), subject combinations are not locked. This is the optimal intervention window."
                    })
                    options.append({
                        "remediation": "Pivot target courses. Consider courses like BA Hons English, Journalism, or specific Arts programs that do not require math.",
                        "feasibility": "HIGH",
                        "action_item": "Counselor to run interest inventory for non-math programs.",
                        "reasoning": "Pivoting targets early avoids structural locks."
                    })
                elif class_level == 11:
                    options.append({
                        "remediation": "Request board registration change. CBSE allows correction of subjects in Class 11 before final registration lists are submitted.",
                        "feasibility": "MEDIUM",
                        "action_item": "Submit a formal written request signed by parents to school principal to switch an elective to Mathematics.",
                        "reasoning": "Feasible but subject to school availability and board deadlines."
                    })
                else: # Class 12
                    options.append({
                        "remediation": "Pivot targets to courses not requiring Mathematics, or universities that do not enforce the subject rule (e.g. private universities like Ashoka University or regional colleges).",
                        "feasibility": "HIGH",
                        "action_item": "Modify targets in counseling tracker. Explore BA Business Administration or BCA at colleges where math is not mandatory.",
                        "reasoning": "At Class 12, adding a main subject like Math in boards is generally not permitted by CBSE, making target pivoting the most realistic solution."
                    })
                    options.append({
                        "remediation": "Add Mathematics as an additional subject and write exams as a private candidate in the subsequent board cycle.",
                        "feasibility": "LOW",
                        "action_item": "Register as a private candidate for CBSE additional math exam.",
                        "reasoning": "Delays admissions by one full year, but satisfies the compliance check."
                    })
            elif subject == "Further Mathematics":
                # Primarily A-levels or UK
                options.append({
                    "remediation": "Register for AP Calculus BC (Advanced Placement) as a private candidate. Cambridge and other top UK universities accept AP Calculus BC (Score 5) as equivalent to Further Mathematics for CBSE board students.",
                    "feasibility": "MEDIUM",
                    "action_item": "Register for AP Calculus BC via College Board India (registration closes March/April) and begin advanced calculus syllabus preparation.",
                    "reasoning": "Allows CBSE students to bridge the math gap without having a Further Maths curriculum in their board."
                })
                options.append({
                    "remediation": "Focus on high TMUA admissions test score. Scoring 6.5+ in TMUA provides strong mathematical proof to override missing Further Maths in CBSE.",
                    "feasibility": "MEDIUM",
                    "action_item": "Enroll in advanced TMUA preparation course, practicing STEP Foundation modules.",
                    "reasoning": "Compensates for syllabus gaps through standardised test excellence."
                })
                options.append({
                    "remediation": "Pivot targets to UK programs with less rigorous math requirements. e.g. Imperial Computing accepts CBSE Math with 95%+ without Further Maths.",
                    "feasibility": "HIGH",
                    "action_item": "Change Cambridge target to Imperial College London or UCL (University College London).",
                    "reasoning": "Saves application slot for high-chance targets."
                })

        elif gap_type == "cuet_unlawful_domain":
            options.append({
                "remediation": "CORRECT CUET APPLICATION: Log into NTA portal during active correction window (closing in 48 hours) and REMOVE the mismatched subject. Replace it with a subject studied in Class 12 Boards (e.g. Computer Science).",
                "feasibility": "HIGH",
                "action_item": "Counselor to guide student in logging into the CUET candidate login, updating paper selections, and downloading the revised confirmation page.",
                "reasoning": "NTA correction window is short and unforgiving. Fixing the selection now prevents absolute disqualification at Delhi University."
            })
            options.append({
                "remediation": "Pivot targets to universities that do not enforce matching board rules. Private universities and other central/state universities often allow any CUET domain combinations.",
                "feasibility": "MEDIUM",
                "action_item": "Add private universities to target dashboard (e.g. BML Munjal, Bennett University) as safety nets.",
                "reasoning": "Protects student options if correction window is missed."
            })

        elif gap_type == "cuet_missing_subject":
            options.append({
                "remediation": "Add Mathematics to CUET registration. You studied Math in boards but omitted it in CUET.",
                "feasibility": "HIGH",
                "action_item": "Add Mathematics paper during the CUET registration correction window.",
                "reasoning": "Since student studied Math in boards, they are legally permitted to take the CUET Math exam. Resolves B.Sc CS/BA Eco prerequisite."
            })

        elif gap_type == "test_missing":
            if subject == "SAT Exam":
                options.append({
                    "remediation": "Register for the August or October SAT exam sessions immediately. MIT and Stanford require SAT/ACT scores.",
                    "feasibility": "HIGH",
                    "action_item": "Register on College Board portal, choose target test center, and draft a 12-week study plan focusing on SAT math and verbal sections.",
                    "reasoning": "Allows scores to be ready in time for early Action (Nov 1)."
                })

        elif gap_type == "test_score_low":
            if subject == "SAT Score":
                options.append({
                    "remediation": "Re-take the SAT. Ananya's score of 1480 is excellent, but for MIT STEM, a math sub-score of 780-800 is normal. Focused practice on SAT Math section can bridge the gap.",
                    "feasibility": "HIGH",
                    "action_item": "Complete 5 mock SAT Math papers under timed conditions. Target December SAT for Regular Decision.",
                    "reasoning": "Score improvements are highly standard through targeted practice."
                })
                options.append({
                    "remediation": "Apply to Test-Optional top-tier US universities (e.g. Columbia, Chicago, NYU) instead of Test-Required institutions.",
                    "feasibility": "HIGH",
                    "action_item": "Adjust US targets in Counselor list to align with test-optional policies.",
                    "reasoning": "Ensures academic credentials are not filtered out by SAT score."
                })

        elif gap_type == "grade_cutoff_violation":
            options.append({
                "remediation": "Target Board Improvement Exams. CBSE allows students to sit for improvement exams in up to two subjects in July to boost their aggregate score.",
                "feasibility": "MEDIUM",
                "action_item": "Fill CBSE Improvement Exam forms for Physics/Chemistry to raise aggregate above 75%.",
                "reasoning": "Direct path to satisfy the JEE board grade criteria."
            })
            options.append({
                "remediation": "Check top 20 board percentile cutoff. If the student falls within the top 20 percentile of CBSE in their category, they satisfy JEE eligibility despite having <75% aggregate.",
                "feasibility": "MEDIUM",
                "action_item": "Counsellor to verify board percentile archives from JoSAA official portal.",
                "reasoning": "Saves preparation effort if percentile criteria is met."
            })
            options.append({
                "remediation": "Pivot target courses. Several top engineering institutes (e.g., IIIT Hyderabad, specific private universities) do not require 75% board aggregate, using only JEE rank.",
                "feasibility": "HIGH",
                "action_item": "Counselor to search alternate counseling codes for IIITs and DTU/NSUT state seats.",
                "reasoning": "Expands target lists with realistic backups."
            })

        elif gap_type == "portfolio_gap":
            if class_level <= 11:
                options.append({
                    "remediation": "Initiate a structured capstone project. For STEM, construct a fully functional application, write a research draft, or build a working robotics assembly.",
                    "feasibility": "HIGH",
                    "action_item": "Assign student to the school's Innovation Lab or match with a mentor for an external project (e.g. open source contribution).",
                    "reasoning": "Class 11 leaves ample time (12 months+) to build a Tier 1 or Tier 2 portfolio signal."
                })
            else: # Class 12 (limited time)
                options.append({
                    "remediation": "Package existing work. Convert internal school science projects, club achievements, or minor coding scripts into a clean GitHub repository or online portfolio page.",
                    "feasibility": "HIGH",
                    "action_item": "Counselor to review student's rough files, help document their work, and publish it on GitHub/personal website.",
                    "reasoning": "Leverages past work quickly before Early Action deadlines (2-3 months left)."
                })
                options.append({
                    "remediation": "Apply to science fairs or school hackathons. Winning a regional certificate can raise a basic club activity to a certified Tier 2 achievement.",
                    "feasibility": "MEDIUM",
                    "action_item": "Submit projects to upcoming local exhibitions.",
                    "reasoning": "Provides verified third-party proof of skill."
                })

        return options
