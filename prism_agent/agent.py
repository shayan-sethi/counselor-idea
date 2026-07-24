import time
import re
import os
import json
from rich.console import Console
from rich.panel import Panel
from .knowledge_graph import KnowledgeGraph
from .reasoner import Reasoner
from .planner import Planner

class PRISMAgent:
    def __init__(self, kg: KnowledgeGraph, reasoner: Reasoner, planner: Planner):
        self.kg = kg
        self.reasoner = reasoner
        self.planner = planner
        self.console = Console()

    # Define tools for LLM
    def fetch_student(self, student_id: str) -> str:
        """
        Fetches the student profile details for the given student ID.
        
        Args:
            student_id: The ID of the student (e.g. 'STU_001').
            
        Returns:
            JSON string of the student profile.
        """
        try:
            with open("data/students_db.json", "r") as f:
                students = json.load(f)
            for s in students:
                if s["id"] == student_id:
                    return json.dumps(s)
        except Exception as e:
            return f"Error: {e}"
        return "Student not found."

    def fetch_requirements(self, target_id: str) -> str:
        """
        Queries the knowledge graph for target course or exam prerequisites.
        
        Args:
            target_id: The target ID (e.g. 'JEE_MAIN', 'CUET_DU_CS').
            
        Returns:
            JSON string of the target requirements.
        """
        target = self.kg.get_course_or_exam(target_id)
        if target:
            return json.dumps(target)
        return "Target not found."

    def check_subjects(self, target_id: str, student_id: str, simulated_subjects: str = "") -> str:
        """
        Verifies if student's board and CUET subjects meet the target prerequisites.
        
        Args:
            target_id: The target pathway ID.
            student_id: The student ID.
            simulated_subjects: Optional comma-separated list of simulated subjects.
            
        Returns:
            JSON array of subject gaps.
        """
        target = self.kg.get_course_or_exam(target_id)
        if not target:
            return "Error: Target not found."
        try:
            with open("data/students_db.json", "r") as f:
                students = json.load(f)
            student = next((s for s in students if s["id"] == student_id), None)
        except Exception as e:
            return f"Error loading student: {e}"
        if not student:
            return "Error: Student not found."
        gaps = []
        subjects = student.get("board_subjects", [])
        if simulated_subjects:
            subjects = [s.strip() for s in simulated_subjects.split(",") if s.strip()]
        norm_subjects = [s.lower().strip() for s in subjects]
        self.reasoner._check_subject_prerequisites(target, norm_subjects, student, gaps)
        if target.get("track") == "India" and "CUET_UG" in target.get("admission_tests", []):
            self.reasoner._check_cuet_domain_alignment(target, norm_subjects, student, gaps)
        return json.dumps(gaps)

    def check_grades(self, target_id: str, student_id: str) -> str:
        """
        Verifies if student's board grades and SAT score meet target cutoffs.
        
        Args:
            target_id: The target pathway ID.
            student_id: The student ID.
            
        Returns:
            JSON array of grade gaps.
        """
        target = self.kg.get_course_or_exam(target_id)
        if not target:
            return "Error: Target not found."
        try:
            with open("data/students_db.json", "r") as f:
                students = json.load(f)
            student = next((s for s in students if s["id"] == student_id), None)
        except Exception as e:
            return f"Error loading student: {e}"
        if not student:
            return "Error: Student not found."
        gaps = []
        self.reasoner._check_grade_prerequisites(target, student, gaps)
        return json.dumps(gaps)

    def check_timeline(self, target_id: str) -> str:
        """
        Checks registration deadlines and timelines for the target.
        
        Args:
            target_id: The target pathway ID.
            
        Returns:
            JSON array of deadline gaps.
        """
        target = self.kg.get_course_or_exam(target_id)
        if not target:
            return "Error: Target not found."
        gaps = []
        self.reasoner._check_deadlines(target, gaps)
        return json.dumps(gaps)

    def check_portfolio(self, target_id: str, student_id: str) -> str:
        """
        Checks if the student's extracurricular portfolio tier is sufficient.
        
        Args:
            target_id: The target pathway ID.
            student_id: The student ID.
            
        Returns:
            JSON array of portfolio gaps.
        """
        target = self.kg.get_course_or_exam(target_id)
        if not target:
            return "Error: Target not found."
        try:
            with open("data/students_db.json", "r") as f:
                students = json.load(f)
            student = next((s for s in students if s["id"] == student_id), None)
        except Exception as e:
            return f"Error loading student: {e}"
        if not student:
            return "Error: Student not found."
        gaps = []
        self.reasoner._check_portfolio_tier(target, student, gaps)
        return json.dumps(gaps)

    def draft_remediations(self, target_id: str, student_id: str, gaps_json: str) -> str:
        """
        Generates feasibility-ranked remediation options for the gaps.
        
        Args:
            target_id: The target pathway ID.
            student_id: The student ID.
            gaps_json: JSON string of the gaps list.
            
        Returns:
            JSON array of remediations.
        """
        target = self.kg.get_course_or_exam(target_id)
        if not target:
            return "Error: Target not found."
        try:
            with open("data/students_db.json", "r") as f:
                students = json.load(f)
            student = next((s for s in students if s["id"] == student_id), None)
        except Exception as e:
            return f"Error loading student: {e}"
        if not student:
            return "Error: Student not found."
        gaps = json.loads(gaps_json)
        temp_analysis = {
            "student_id": student_id,
            "class_level": student["class_level"],
            "targets": {
                target_id: {
                    "target_name": target["name"],
                    "track": target["track"],
                    "compliant": len(gaps) == 0,
                    "urgency_score": self.reasoner._calculate_urgency(gaps),
                    "gaps": gaps
                }
            }
        }
        rems = self.planner.get_remediations(temp_analysis)
        return json.dumps(rems.get(target_id, []))

    def solve_goal(self, student_id, target_id, students_list, simulated_subjects=None, silent=False):
        import google.generativeai as genai
        import os
        import json

        api_key = os.environ.get("GEMINI_API_KEY", "")
        if not api_key:
            return self._solve_goal_simulated(student_id, target_id, students_list, simulated_subjects, silent)

        genai.configure(api_key=api_key)

        prompt = f"""You are the PRISM Compliance Agent. Your goal is to evaluate compliance and design remediations for student {student_id} targeting course/exam {target_id}.
Follow this sequence exactly to solve the goal:
1. Retrieve the student profile using `fetch_student`.
2. Retrieve target requirements using `fetch_requirements`.
3. Check subjects prerequisite compliance using `check_subjects`. (Pass the simulated_subjects override string if one was provided in the context, otherwise empty).
4. Check academic grade cutoffs using `check_grades`.
5. Check timeline deadlines using `check_timeline`.
6. Check extracurricular portfolio requirements using `check_portfolio`.
7. Call `draft_remediations` with the list of ALL gaps found across all checks.
8. Formulate a final response. Output a single JSON block at the very end of your response with the following format:
{{
  "compliant": true/false,
  "urgency_score": <number>,
  "gaps": <array of gap objects>,
  "remediations": <array of remediation objects>
}}

Write a sentence explaining your thought before calling each tool.
"""

        tools = [
            self.fetch_student,
            self.fetch_requirements,
            self.check_subjects,
            self.check_grades,
            self.check_timeline,
            self.check_portfolio,
            self.draft_remediations
        ]

        trace = []

        model = genai.GenerativeModel(
            model_name="gemini-1.5-flash",
            tools=tools,
            generation_config={"temperature": 0.0}
        )

        chat = model.start_chat()
        response = chat.send_message(prompt)

        for _ in range(15):
            parts = response.candidates[0].content.parts
            has_function_calls = False
            function_responses = []

            for part in parts:
                # Record thought if text is generated
                if part.text:
                    trace.append({
                        "type": "thought",
                        "message": part.text.strip()
                    })
                    if not silent:
                        self.console.print(f"\n[bold magenta]Thought:[/bold magenta] {part.text.strip()}")

                if part.function_call:
                    has_function_calls = True
                    fc = part.function_call
                    args_dict = dict(fc.args)
                    trace.append({
                        "type": "action",
                        "message": f"call_tool: {fc.name}",
                        "detail": json.dumps(args_dict)
                    })
                    if not silent:
                        self.console.print(f"[bold cyan]Action:[/bold cyan] call_tool [yellow]{fc.name}[/yellow] with ({json.dumps(args_dict)})")

                    # Execute tool
                    tool_func = getattr(self, fc.name, None)
                    if tool_func:
                        try:
                            observation = tool_func(**args_dict)
                        except Exception as e:
                            observation = f"Error: {e}"
                    else:
                        observation = f"Error: Tool {fc.name} not found."

                    trace.append({
                        "type": "observation",
                        "message": observation
                    })
                    if not silent:
                        self.console.print(f"[dim green]Observation: {observation[:200]}...[/dim green]")

                    function_responses.append(
                        genai.types.Part.from_function_response(
                            name=fc.name,
                            response={"result": observation}
                        )
                    )

            if has_function_calls:
                response = chat.send_message(function_responses)
            else:
                break

        # Extract final answer
        final_text = response.text
        try:
            json_match = re.search(r"\{.*\}", final_text, re.DOTALL)
            if json_match:
                final_data = json.loads(json_match.group(0))
            else:
                final_data = json.loads(final_text)
        except Exception:
            final_data = self._solve_goal_fallback(student_id, target_id, students_list, simulated_subjects)

        # Ensure keys are present
        final_data["trace"] = trace
        target = self.kg.get_course_or_exam(target_id)
        if target:
            final_data["target_name"] = target["name"]
            final_data["track"] = target["track"]

        return final_data

    def _solve_goal_fallback(self, student_id, target_id, students_list, simulated_subjects):
        student = next((s for s in students_list if s["id"] == student_id), None)
        target = self.kg.get_course_or_exam(target_id)
        if not student or not target:
            return {"compliant": True, "match_score": 100, "risk_level": "Strong Match", "urgency_score": 0, "gaps": [], "remediations": []}
        
        gaps = []
        subjects = simulated_subjects if simulated_subjects is not None else student.get("board_subjects", [])
        if isinstance(subjects, str):
            subjects = [s.strip() for s in subjects.split(",") if s.strip()]
        norm_subjects = [s.lower().strip() for s in subjects]
        
        self.reasoner._check_subject_prerequisites(target, norm_subjects, student, gaps)
        if target.get("track") == "India" and "CUET_UG" in target.get("admission_tests", []):
            self.reasoner._check_cuet_domain_alignment(target, norm_subjects, student, gaps)
        self.reasoner._check_grade_prerequisites(target, student, gaps)
        self.reasoner._check_deadlines(target, gaps)
        self.reasoner._check_portfolio_tier(target, student, gaps)

        temp_analysis = {
            "student_id": student_id,
            "class_level": student["class_level"],
            "targets": {
                target_id: {
                    "target_name": target["name"],
                    "track": target["track"],
                    "compliant": len(gaps) == 0,
                    "urgency_score": self.reasoner._calculate_urgency(gaps),
                    "gaps": gaps
                }
            }
        }
        remediations = self.planner.get_remediations(temp_analysis).get(target_id, [])
        match_score = self.reasoner._calculate_match_score(gaps)
        risk_level = self.reasoner._risk_level_label(match_score)
        return {
            "compliant": len(gaps) == 0,
            "match_score": match_score,
            "risk_level": risk_level,
            "urgency_score": temp_analysis["targets"][target_id]["urgency_score"],
            "gaps": gaps,
            "remediations": remediations
        }

    def _solve_goal_simulated(self, student_id, target_id, students_list, simulated_subjects=None, silent=False):
        trace = []
        student = next((s for s in students_list if s["id"] == student_id), None)
        target = self.kg.get_course_or_exam(target_id)

        if not student or not target:
            return {"compliant": True, "match_score": 100, "risk_level": "Strong Match", "urgency_score": 0, "gaps": [], "remediations": [], "trace": []}

        # Step 1: fetch_student
        student_name = student.get("name", "Student")
        board = student.get("board", "CBSE")
        class_level = student.get("class_level", 12)
        trace.append({"type": "thought", "message": f"I need to retrieve the profile of student '{student_name}' to inspect their high school system ({board}, Class {class_level}) and studied subjects."})
        trace.append({"type": "action", "message": "call_tool: fetch_student", "detail": json.dumps({"student_id": student_id})})
        trace.append({"type": "observation", "message": json.dumps(student)})

        # Step 2: fetch_requirements
        target_name = target.get("name", "Target")
        track = target.get("track", "UK")
        trace.append({"type": "thought", "message": f"Next, I must query the target requirements database for '{target_name}' (Track: {track}) to identify compliance rules."})
        trace.append({"type": "action", "message": "call_tool: fetch_requirements", "detail": json.dumps({"target_id": target_id})})
        trace.append({"type": "observation", "message": json.dumps(target)})

        # Step 3: check_subjects
        subjects = simulated_subjects if simulated_subjects is not None else student.get("board_subjects", [])
        if isinstance(subjects, str):
            subjects = [s.strip() for s in subjects.split(",") if s.strip()]
        norm_subjects = [s.lower().strip() for s in subjects]
        
        trace.append({"type": "thought", "message": f"Checking subject selection compliance. Comparing studied subjects {subjects} against mandatory pathway prerequisites."})
        trace.append({"type": "action", "message": "call_tool: check_subjects", "detail": json.dumps({"target_id": target_id, "student_id": student_id})})
        gaps = []
        self.reasoner._check_subject_prerequisites(target, norm_subjects, student, gaps)
        if target.get("track") == "India" and "CUET_UG" in target.get("admission_tests", []):
            self.reasoner._check_cuet_domain_alignment(target, norm_subjects, student, gaps)
        trace.append({"type": "observation", "message": json.dumps(gaps)})

        # Step 4: check_grades
        expected_pct = student.get("grades", {}).get("current_expected_board", "0%")
        trace.append({"type": "thought", "message": f"Evaluating academic cutoffs. Expected Class 12 aggregate is {expected_pct}. Verifying individual subject scores if present."})
        trace.append({"type": "action", "message": "call_tool: check_grades", "detail": json.dumps({"target_id": target_id, "student_id": student_id})})
        grade_gaps = []
        self.reasoner._check_grade_prerequisites(target, student, grade_gaps)
        gaps.extend(grade_gaps)
        trace.append({"type": "observation", "message": json.dumps(grade_gaps)})

        # Step 5: check_timeline
        deadlines = [d.get("label", "Deadline") for d in target.get("deadlines", [])]
        trace.append({"type": "thought", "message": f"Verifying timeline constraints and milestones: {', '.join(deadlines) if deadlines else 'None'}. Checking register actions."})
        trace.append({"type": "action", "message": "call_tool: check_timeline", "detail": json.dumps({"target_id": target_id})})
        timeline_gaps = []
        self.reasoner._check_deadlines(target, timeline_gaps)
        gaps.extend(timeline_gaps)
        trace.append({"type": "observation", "message": json.dumps(timeline_gaps)})

        # Step 6: check_portfolio
        activities = [p.get("activity", "Activity") for p in student.get("portfolio", [])]
        trace.append({"type": "thought", "message": f"Checking extracurricular portfolio compatibility. Classifying student achievements: {', '.join(activities) if activities else 'None'}."})
        trace.append({"type": "action", "message": "call_tool: check_portfolio", "detail": json.dumps({"target_id": target_id, "student_id": student_id})})
        portfolio_gaps = []
        self.reasoner._check_portfolio_tier(target, student, portfolio_gaps)
        gaps.extend(portfolio_gaps)
        trace.append({"type": "observation", "message": json.dumps(portfolio_gaps)})

        # Step 7: draft_remediations
        remediations = []
        if gaps:
            trace.append({"type": "thought", "message": f"Discovered {len(gaps)} compliance gap(s). Querying Planner Engine to formulate and rank remediation paths."})
            trace.append({"type": "action", "message": "call_tool: draft_remediations", "detail": json.dumps({"target_id": target_id, "student_id": student_id, "gaps_json": json.dumps(gaps)})})
            temp_analysis = {
                "student_id": student_id,
                "class_level": student["class_level"],
                "targets": {
                    target_id: {
                        "target_name": target["name"],
                        "track": target["track"],
                        "compliant": len(gaps) == 0,
                        "urgency_score": self.reasoner._calculate_urgency(gaps),
                        "gaps": gaps
                    }
                }
            }
            remediations = self.planner.get_remediations(temp_analysis).get(target_id, [])
            trace.append({"type": "observation", "message": json.dumps(remediations)})
        else:
            trace.append({"type": "thought", "message": "No compliance gaps discovered. Candidate is 100% on track for this target pathway."})

        match_score = self.reasoner._calculate_match_score(gaps)
        risk_level = self.reasoner._risk_level_label(match_score)
        return {
            "compliant": len(gaps) == 0,
            "match_score": match_score,
            "risk_level": risk_level,
            "urgency_score": self.reasoner._calculate_urgency(gaps),
            "gaps": gaps,
            "remediations": remediations,
            "target_name": target["name"],
            "track": target["track"],
            "trace": trace
        }
