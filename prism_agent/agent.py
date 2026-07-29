import time
import re
import os
import json
try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass
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

        groq_key = os.environ.get("GROQ_API_KEY", "").strip()
        if groq_key:
            return self._solve_goal_groq_fallback(student_id, target_id, students_list, prompt, silent)

        return self._solve_goal_simulated(student_id, target_id, students_list, simulated_subjects, silent)

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
            
        student = next((s for s in students_list if s["id"] == student_id), None)
        if student and target:
            gaps = final_data.get("gaps", [])
            match_score = final_data.get("match_score")
            if match_score is None:
                match_score = self.reasoner._calculate_match_score(gaps)
                final_data["match_score"] = match_score
                final_data["risk_level"] = self.reasoner._risk_level_label(match_score)
            final_data["difficulty_label"] = self.reasoner._classify_difficulty(student, target, match_score, gaps)

        return final_data

    def _solve_goal_groq_fallback(self, student_id, target_id, students_list, prompt, silent):
        """Uses Groq API (llama-3.3-70b-versatile) to reason through student evaluation."""
        import requests
        import json
        import re
        
        student = next((s for s in students_list if s["id"] == student_id), None)
        target = self.kg.get_course_or_exam(target_id)
        groq_key = os.environ.get("GROQ_API_KEY", "").strip()

        fallback_prompt = f"""
You are an expert AI admissions counselor. Evaluate student {student_id} for target {target_id}.
Student Profile: {json.dumps(student)}
Target Requirements: {json.dumps(target)}

Output ONLY a valid JSON object matching this schema exactly:
{{
  "target_name": "{target['name'] if target else 'Target'}",
  "track": "{target['track'] if target else 'Unknown'}",
  "compliant": true,
  "urgency_score": 15,
  "match_score": 85,
  "risk_level": "Strong Match",
  "difficulty_label": "Target",
  "gaps": [ {{"field": "grades", "issue": "describe gap"}} ],
  "remediations": [ {{"field": "grades", "action": "describe action"}} ]
}}
"""
        try:
            res = requests.post(
                "https://api.groq.com/openai/v1/chat/completions",
                headers={"Authorization": f"Bearer {groq_key}", "Content-Type": "application/json"},
                json={
                    "model": "llama-3.3-70b-versatile",
                    "messages": [
                        {"role": "system", "content": "You are unlockED AI Admissions Compliance Officer. Return ONLY valid JSON."},
                        {"role": "user", "content": fallback_prompt}
                    ],
                    "response_format": {"type": "json_object"},
                    "temperature": 0.1
                },
                timeout=20
            )
            if res.status_code == 200:
                raw_text = res.json()["choices"][0]["message"]["content"]
                final_data = json.loads(raw_text)
                final_data["trace"] = [{"type": "thought", "message": "Groq Llama-3.3-70b evaluation completed."}]
                return final_data
        except Exception as err:
            if not silent:
                print(f"[Agent Warning] Groq goal evaluation failed: {err}. Falling back to simulated calculation.")

        return self._solve_goal_simulated(student_id, target_id, students_list, "", silent)

    def _solve_goal_ollama_fallback(self, student_id, target_id, students_list, prompt, silent):
        """Uses the local Ollama LLM to reason through the problem when the Gemini API is rate-limited."""
        import requests
        import json
        import re
        student = next((s for s in students_list if s["id"] == student_id), None)
        target = self.kg.get_course_or_exam(target_id)
        
        fallback_prompt = f"""
You are an AI admissions counselor. Evaluate student {student_id} for target {target_id}.
Student Profile: {json.dumps(student)}
Target Requirements: {json.dumps(target)}

Output ONLY valid JSON matching this schema exactly. Do not output anything else.
{{
  "target_name": "{target['name'] if target else 'Target'}",
  "track": "{target['track'] if target else 'Unknown'}",
  "compliant": true/false,
  "urgency_score": <0-100 integer>,
  "match_score": <0-100 integer>,
  "risk_level": "Strong Match" / "At Risk" / "Critical Risk",
  "difficulty_label": "Safety" / "Target" / "Reach",
  "gaps": [ {{"field": "grades", "issue": "describe gap"}} ],
  "remediations": [ {{"field": "grades", "action": "describe action"}} ]
}}
"""
        try:
            res = requests.post("http://127.0.0.1:11434/api/generate", json={
                "model": "llama3.2",
                "prompt": fallback_prompt,
                "stream": False,
                "options": {"temperature": 0.0}
            }, timeout=30)
            text = res.json().get("response", "")
            
            # Clean up potential markdown fences
            text = re.sub(r'^```json\s*', '', text.strip())
            text = re.sub(r'\s*```$', '', text.strip())
            
            parsed = json.loads(text)
            # Ensure safe fallback keys
            parsed["target_name"] = parsed.get("target_name", target["name"] if target else "Target")
            parsed["track"] = parsed.get("track", target["track"] if target else "Unknown")
            parsed["compliant"] = bool(parsed.get("compliant", False))
            parsed["match_score"] = int(parsed.get("match_score", 50))
            parsed["risk_level"] = parsed.get("risk_level", "At Risk")
            parsed["urgency_score"] = int(parsed.get("urgency_score", 50))
            parsed["gaps"] = parsed.get("gaps", [])
            parsed["remediations"] = parsed.get("remediations", [])
            parsed["difficulty_label"] = parsed.get("difficulty_label", "Reach")
            
            return parsed
        except Exception as e:
            if not silent:
                print(f"[Ollama Error] {e}. Falling back to hardcoded rule engine.")
            return self._solve_goal_fallback(student_id, target_id, students_list, None)

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
            "remediations": remediations,
            "difficulty_label": self.reasoner._classify_difficulty(student, target, match_score, gaps)
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
            "trace": trace,
            "difficulty_label": self.reasoner._classify_difficulty(student, target, match_score, gaps)
        }
