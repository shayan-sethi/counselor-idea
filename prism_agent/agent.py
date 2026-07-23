import time
import re
from rich.console import Console
from rich.panel import Panel
from rich.text import Text
from .knowledge_graph import KnowledgeGraph
from .reasoner import Reasoner
from .planner import Planner

class AgentTool:
    def __init__(self, name, description, func):
        self.name = name
        self.description = description
        self.func = func

    def execute(self, *args, **kwargs):
        return self.func(*args, **kwargs)


class PRISMAgent:
    def __init__(self, kg: KnowledgeGraph, reasoner: Reasoner, planner: Planner):
        self.kg = kg
        self.reasoner = reasoner
        self.planner = planner
        self.console = Console()
        self.tools = {}
        self.setup_tools()

    def setup_tools(self):
        """Registers the set of local tools the agent can execute during its loop."""
        self.tools["fetch_student"] = AgentTool(
            "fetch_student",
            "Fetches a student's full profile by their ID.",
            self._tool_fetch_student
        )
        self.tools["fetch_requirements"] = AgentTool(
            "fetch_requirements",
            "Queries the requirements graph for a target course/exam.",
            self._tool_fetch_requirements
        )
        self.tools["check_subjects"] = AgentTool(
            "check_subjects",
            "Verifies board & CUET domain subject prerequisites.",
            self._tool_check_subjects
        )
        self.tools["check_grades"] = AgentTool(
            "check_grades",
            "Verifies board aggregate and SAT/ACT cutoff compliance.",
            self._tool_check_grades
        )
        self.tools["check_timeline"] = AgentTool(
            "check_timeline",
            "Checks registration deadlines and correction window remaining hours.",
            self._tool_check_timeline
        )
        self.tools["check_portfolio"] = AgentTool(
            "check_portfolio",
            "Evaluates extracurricular achievements against target requirements.",
            self._tool_check_portfolio
        )
        self.tools["draft_remediations"] = AgentTool(
            "draft_remediations",
            "Generates ranked remediation options for all gaps discovered.",
            self._tool_draft_remediations
        )

    # Tool Implementations
    def _tool_fetch_student(self, student_id, students_list):
        for s in students_list:
            if s["id"] == student_id:
                return s
        return None

    def _tool_fetch_requirements(self, target_id):
        return self.kg.get_course_or_exam(target_id)

    def _tool_check_subjects(self, target, student, simulated_subjects=None):
        gaps = []
        subjects = simulated_subjects if simulated_subjects is not None else student.get("board_subjects", [])
        norm_subjects = [s.lower().strip() for s in subjects]
        self.reasoner._check_subject_prerequisites(target, norm_subjects, student, gaps)
        if target.get("track") == "India" and "CUET_UG" in target.get("admission_tests", []):
            self.reasoner._check_cuet_domain_alignment(target, norm_subjects, student, gaps)
        return gaps

    def _tool_check_grades(self, target, student):
        gaps = []
        self.reasoner._check_grade_prerequisites(target, student, gaps)
        return gaps

    def _tool_check_timeline(self, target):
        gaps = []
        self.reasoner._check_deadlines(target, gaps)
        return gaps

    def _tool_check_portfolio(self, target, student):
        gaps = []
        self.reasoner._check_portfolio_tier(target, student, gaps)
        return gaps

    def _tool_draft_remediations(self, target_id, student_analysis):
        remediations = self.planner.get_remediations(student_analysis)
        return remediations.get(target_id, [])

    def solve_goal(self, student_id, target_id, students_list, simulated_subjects=None, silent=False):
        """
        Executes a step-by-step ReAct (Reasoning + Action) execution loop to solve
        a specific student matriculation target compliance check.
        """
        if not silent:
            self.console.print(Panel(
                f"[bold green]Starting Autonomous AI Agent Execution Loop[/bold green]\n"
                f"Goal: Evaluate compliance and design remediation path for student [cyan]{student_id}[/cyan] targeting [cyan]{target_id}[/cyan]",
                border_style="green"
            ))

        trace = []
        student = None
        target = None
        gaps = []
        
        # Step 1: Perception (Load student data)
        if not silent:
            self._print_thought("I need to retrieve the student's profile to inspect subjects and grades.")
            self._print_action("fetch_student", f"student_id='{student_id}'")
        
        student = self.tools["fetch_student"].execute(student_id, students_list)
        if not student:
            if not silent:
                self.console.print("[red]Observation: Student not found. Aborting.[/red]")
            return None

        if not silent:
            self.console.print(f"[dim green]Observation: Retrieved profile for '{student['name']}'. board={student['board']}, class={student['class_level']}[/dim green]")
            time.sleep(0.3)

        # Step 2: Query Knowledge Graph
        if not silent:
            self._print_thought(f"Now I must query the requirements graph for target node '{target_id}' to fetch subject rules and deadlines.")
            self._print_action("fetch_requirements", f"target_id='{target_id}'")
        
        target = self.tools["fetch_requirements"].execute(target_id)
        if not target:
            if not silent:
                self.console.print(f"[red]Observation: Target '{target_id}' not found in requirements graph. Aborting.[/red]")
            return None

        if not silent:
            self.console.print(f"[dim green]Observation: Target rules loaded. Track: {target['track']}. Prereqs defined: {len(target['subject_prerequisites'])} subjects.[/dim green]")
            time.sleep(0.3)

        # Step 3: Check Subjects
        if not silent:
            self._print_thought("First, I will run the subject verification checks to search for missing prerequisites or CUET domain-matching violations.")
            self._print_action("check_subjects", f"student='{student_id}', target='{target_id}'")
        
        subject_gaps = self.tools["check_subjects"].execute(target, student, simulated_subjects)
        gaps.extend(subject_gaps)

        if not silent:
            if subject_gaps:
                self.console.print(f"[bold yellow]Observation: Found {len(subject_gaps)} subject-selection gaps.[/bold yellow]")
                for g in subject_gaps:
                    self.console.print(f"  - [yellow]{g['description']}[/yellow]")
            else:
                self.console.print("[dim green]Observation: Subjects list meets all target prerequisites.[/dim green]")
            time.sleep(0.3)

        # Step 4: Check Grades
        if not silent:
            self._print_thought("Next, I will verify academic aggregate score compatibility (CBSE / SAT cutoffs).")
            self._print_action("check_grades", f"student='{student_id}', target='{target_id}'")
        
        grade_gaps = self.tools["check_grades"].execute(target, student)
        gaps.extend(grade_gaps)

        if not silent:
            if grade_gaps:
                self.console.print(f"[bold yellow]Observation: Identified grade boundary failures.[/bold yellow]")
                for g in grade_gaps:
                    self.console.print(f"  - [yellow]{g['description']}[/yellow]")
            else:
                self.console.print("[dim green]Observation: Grade requirements satisfied.[/dim green]")
            time.sleep(0.3)

        # Step 5: Check Deadlines
        if not silent:
            self._print_thought("I need to perform deadline proximity analysis relative to the active admission cycle.")
            self._print_action("check_timeline", f"target='{target_id}'")
        
        timeline_gaps = self.tools["check_timeline"].execute(target)
        gaps.extend(timeline_gaps)

        if not silent:
            if timeline_gaps:
                self.console.print(f"[bold yellow]Observation: Found active timeline issues.[/bold yellow]")
                for g in timeline_gaps:
                    self.console.print(f"  - [yellow]{g['description']}[/yellow]")
            else:
                self.console.print("[dim green]Observation: No immediate timeline risks detected.[/dim green]")
            time.sleep(0.3)

        # Step 6: Check Portfolio
        if not silent:
            self._print_thought("I will evaluate the extracurricular portfolio tier against the selectivity benchmarks.")
            self._print_action("check_portfolio", f"student='{student_id}', target='{target_id}'")
        
        portfolio_gaps = self.tools["check_portfolio"].execute(target, student)
        gaps.extend(portfolio_gaps)

        if not silent:
            if portfolio_gaps:
                self.console.print(f"[bold yellow]Observation: Stated targets expect higher portfolio signals.[/bold yellow]")
                for g in portfolio_gaps:
                    self.console.print(f"  - [yellow]{g['description']}[/yellow]")
            else:
                self.console.print("[dim green]Observation: Extracurricular portfolio level matches requirements.[/dim green]")
            time.sleep(0.3)

        # Compile temporary analysis to pass into planner tool
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

        # Step 7: Draft Remediation
        remediations = []
        if gaps:
            if not silent:
                self._print_thought("Since gaps were flagged, I will run the Remediation Planner to calculate ranked paths based on current timeline feasibility.")
                self._print_action("draft_remediations", f"target='{target_id}'")
            
            remediations = self.tools["draft_remediations"].execute(target_id, temp_analysis)
            
            if not silent:
                self.console.print(f"[dim green]Observation: Generated {len(remediations)} remediation paths ranked by feasibility.[/dim green]")
                time.sleep(0.3)

        # Final Answer
        if not silent:
            self.console.print("\n[bold green]✔ Final Answer Formulated. Terminating agent loop.[/bold green]")
            time.sleep(0.2)

        return {
            "compliant": len(gaps) == 0,
            "urgency_score": temp_analysis["targets"][target_id]["urgency_score"],
            "gaps": gaps,
            "remediations": remediations,
            "target_name": target["name"],
            "track": target["track"]
        }

    def _print_thought(self, thought_msg):
        self.console.print(f"\n[bold magenta]Thought:[/bold magenta] {thought_msg}")

    def _print_action(self, tool_name, args):
        self.console.print(f"[bold cyan]Action:[/bold cyan] call_tool [yellow]{tool_name}[/yellow] with arguments ({args})")
