import os
import json
import datetime
from rich.console import Console
from rich.table import Table
from rich.panel import Panel
from rich.tree import Tree
from rich.text import Text
from rich.prompt import Prompt
from rich.align import Align
from .knowledge_graph import KnowledgeGraph
from .reasoner import Reasoner
from .planner import Planner
from .agent import PRISMAgent

class CounselorDashboard:
    def __init__(self, students_db_path=None, requirements_db_path=None):
        base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        
        if students_db_path is None:
            students_db_path = os.path.join(base_dir, "data", "students_db.json")
        if requirements_db_path is None:
            requirements_db_path = os.path.join(base_dir, "data", "requirements_db.json")
            
        self.students_path = students_db_path
        self.kg = KnowledgeGraph(requirements_db_path)
        self.reasoner = Reasoner(self.kg)
        self.planner = Planner()
        self.agent = PRISMAgent(self.kg, self.reasoner, self.planner)
        self.console = Console()
        self.students = []
        self.load_students()

    def load_students(self):
        """Loads students from JSON file."""
        if not os.path.exists(self.students_path):
            raise FileNotFoundError(f"Students database not found at: {self.students_path}")
        
        with open(self.students_path, "r") as f:
            self.students = json.load(f)

    def run(self):
        """Main dashboard execution loop."""
        while True:
            self.clear_screen()
            self.show_header()
            
            # Evaluate current student cohort
            analysis_results = self.reasoner.evaluate_cohort(self.students)
            
            # Display Cohort Metrics
            self.display_metrics(analysis_results)
            
            # Display Student Status Table
            self.display_cohort_table(analysis_results)
            
            # Action prompt
            self.console.print("\n[bold cyan]Dashboard Actions:[/bold cyan]")
            self.console.print("[yellow]1-6[/yellow] : Inspect specific student profile & view remediations")
            self.console.print("[yellow]s[/yellow]   : Run Subject Pivot Simulator (Hypothetical analysis)")
            self.console.print("[yellow]e[/yellow]   : Export full compliance audit report to JSON (for Frontend)")
            self.console.print("[yellow]q[/yellow]   : Exit Counselor Co-pilot")
            
            choice = Prompt.ask("\nEnter option", default="q")
            
            if choice.isdigit():
                idx = int(choice) - 1
                if 0 <= idx < len(self.students):
                    self.inspect_student(self.students[idx], analysis_results[self.students[idx]["id"]])
                else:
                    self.press_enter_to_continue("Invalid student selection number.")
            elif choice.lower() == 's':
                self.run_pivot_simulator()
            elif choice.lower() == 'e':
                self.export_report(analysis_results)
            elif choice.lower() == 'q':
                self.console.print("\n[bold green]Goodbye! Thank you for using PRISM.[/bold green]")
                break
            else:
                self.press_enter_to_continue("Unknown command.")

    def clear_screen(self):
        """Clears the console screen."""
        os.system('cls' if os.name == 'nt' else 'clear')

    def show_header(self):
        header_text = Text("PRISM: Prerequisite & Risk Intervention System for Matriculation", style="bold white")
        sub_text = Text("B2B AI Counselor Co-pilot | compliance-first dual-track fact engine", style="italic cyan")
        self.console.print(Panel(Align.center(Text.assemble(header_text, "\n", sub_text)), border_style="bold blue"))

    def display_metrics(self, analysis_results):
        """Displays quick cohort metrics panel."""
        total_students = len(self.students)
        high_risk_students = 0
        compliant_students = 0
        total_gaps = 0
        upcoming_deadlines_count = 0

        # Math logic for deadlines
        current_date = datetime.date(2026, 7, 22)
        for target in self.kg.get_all_targets():
            for dl in target.get("deadlines", []):
                dl_date = datetime.datetime.strptime(dl["date"], "%Y-%m-%d").date()
                diff_days = (dl_date - current_date).days
                if 0 <= diff_days <= 30:
                    upcoming_deadlines_count += 1

        for stu_id, res in analysis_results.items():
            stu_compliant = True
            for target_id, t_res in res["targets"].items():
                if not t_res["compliant"]:
                    stu_compliant = False
                    total_gaps += len(t_res["gaps"])
                if t_res["urgency_score"] >= 35:
                    high_risk_students += 1
            
            if stu_compliant:
                compliant_students += 1

        metrics_text = Text()
        metrics_text.append(f"Cohort Size: {total_students} | ", style="bold white")
        metrics_text.append(f"Fully Compliant: {compliant_students} | ", style="bold green")
        metrics_text.append(f"High Risk Alert Queue: {high_risk_students} | ", style="bold red")
        metrics_text.append(f"Total Active Gaps: {total_gaps} | ", style="bold yellow")
        metrics_text.append(f"Urgent Deadlines (<30 Days): {upcoming_deadlines_count}", style="bold magenta")
        
        self.console.print(Panel(Align.center(metrics_text), border_style="dim white", title="Cohort Statistics"))

    def display_cohort_table(self, analysis_results):
        """Renders cohort overview table."""
        table = Table(show_header=True, header_style="bold magenta", expand=True)
        table.add_column("No.", style="dim", width=4)
        table.add_column("Student Name", style="bold white")
        table.add_column("Class", style="white")
        table.add_column("Target Aspirations", style="cyan")
        table.add_column("Max Urgency", justify="center")
        table.add_column("Risk Status", justify="center")

        for idx, student in enumerate(self.students):
            stu_id = student["id"]
            res = analysis_results[stu_id]
            
            # Calculate overall max risk and build aspiration string
            max_urgency = 0
            aspiration_names = []
            has_gaps = False
            
            for target_id, target_res in res["targets"].items():
                max_urgency = max(max_urgency, target_res["urgency_score"])
                aspiration_names.append(target_res["target_name"])
                if not target_res["compliant"]:
                    has_gaps = True

            # Format Status Column
            if not has_gaps:
                status_str = Text("✔ PASS", style="bold green")
            elif max_urgency >= 35:
                status_str = Text(f"☠ CRITICAL RISK ({max_urgency})", style="bold red")
            else:
                status_str = Text(f"⚠ WARNING ({max_urgency})", style="bold yellow")

            # Format max urgency bar
            urgency_bar = f"{max_urgency}%"
            if max_urgency >= 35:
                urgency_style = "bold red"
            elif max_urgency > 0:
                urgency_style = "bold yellow"
            else:
                urgency_style = "bold green"
                
            table.add_row(
                str(idx + 1),
                student["name"],
                f"Class {student['class_level']}",
                ", ".join(aspiration_names),
                Text(urgency_bar, style=urgency_style),
                status_str
            )

        self.console.print(table)

    def inspect_student(self, student, student_analysis, simulated_subjects=None):
        """Displays detailed student report page with gaps and remediation plans."""
        self.clear_screen()
        self.show_header()
        
        is_simulation = simulated_subjects is not None
        title_prefix = "SIMULATED: " if is_simulation else ""
        
        self.console.print(f"\n[bold underline yellow]{title_prefix}STUDENT COMPLIANCE REPORT: {student['name']}[/bold underline yellow]")
        
        # Details panel
        details_table = Table.grid(padding=1)
        details_table.add_row(Text("Class: ", style="bold cyan"), Text(str(student["class_level"])))
        details_table.add_row(Text("Board curriculum: ", style="bold cyan"), Text(student["board"]))
        
        subjects_list = simulated_subjects if is_simulation else student.get("board_subjects", [])
        details_table.add_row(Text("Board Subjects: ", style="bold cyan"), Text(", ".join(subjects_list)))
        
        if student.get("planned_class_11_subjects"):
            details_table.add_row(Text("Planned 11th Subjects: ", style="bold cyan"), Text(", ".join(student["planned_class_11_subjects"])))
            
        if student.get("cuet_subjects"):
            details_table.add_row(Text("CUET Selected Papers: ", style="bold cyan"), Text(", ".join(student["cuet_subjects"])))
            
        # Tests and portfolio
        tests = []
        for test_name, score in student.get("standardized_tests", {}).items():
            tests.append(f"{test_name}: {score}")
        details_table.add_row(Text("Standardised Tests: ", style="bold cyan"), Text(", ".join(tests) if tests else "None"))
        
        portfolio_desc = []
        for item in student.get("portfolio", []):
            portfolio_desc.append(f"[{item['activity']} (Tier {item['tier']})]")
        details_table.add_row(Text("Extracurriculars: ", style="bold cyan"), Text(", ".join(portfolio_desc) if portfolio_desc else "None"))
        
        self.console.print(Panel(details_table, title="Student Details & Academic Profile", border_style="cyan"))

        # Iterate over aspirations and solve them live using the ReAct loop
        for target_id in student.get("targets", []):
            agent_result = self.agent.solve_goal(student["id"], target_id, self.students, simulated_subjects=simulated_subjects)
            
            # Print target heading
            self.console.print(f"\n[bold white]Target Pathway:[/bold white] [bold magenta]{agent_result['target_name']}[/bold magenta] ({agent_result['track']} Track)")
            
            if agent_result["compliant"]:
                self.console.print("[bold green]  ✔ ALL REQUIREMENTS MET & VERIFIED[/bold green]")
                continue
                
            self.console.print("  [bold red]  ❌ COMPLIANCE GAPS FOUND (Risk Score: " + str(agent_result['urgency_score']) + ")[/bold red]")
            
            # Print Gaps with Citations
            tree = Tree("[bold red]Gaps & Infringement Audit Log:[/bold red]")
            for gap in agent_result["gaps"]:
                gap_node = tree.add(f"[bold yellow]{gap['subject'] or 'General'}: {gap['description']}[/bold yellow]")
                gap_node.add(f"[dim white]Citation: {gap['citation']}[/dim white]")
                gap_node.add(f"[dim white]Last Verified: {gap['last_verified']}[/dim white]")
            self.console.print(tree)
            
            # Print Remediation plans
            target_remediations = agent_result["remediations"]
            if target_remediations:
                self.console.print("\n  [bold green]Ranked Compliance Remediation Options:[/bold green]")
                for r_idx, rem in enumerate(target_remediations):
                    feas = rem["feasibility"]
                    f_style = "bold green" if feas == "HIGH" else "bold yellow" if feas == "MEDIUM" else "bold red"
                    
                    self.console.print(f"    [bold cyan]Option {r_idx + 1}:[/bold cyan] {rem['remediation']}")
                    self.console.print(f"      [bold white]Feasibility:[/bold white] [{f_style}]{feas}[/{f_style}]")
                    self.console.print(f"      [bold white]Action Step:[/bold white] {rem['action_item']}")
                    self.console.print(f"      [bold white]Mechanics/Reason:[/bold white] [dim]{rem['reasoning']}[/dim]\n")

        self.press_enter_to_continue("Detail inspection review complete.")

    def run_pivot_simulator(self):
        """Interactive tool to test subject change pivots and recalculate compliance."""
        self.clear_screen()
        self.show_header()
        self.console.print("\n[bold underline yellow]SUBJECT PIVOT SIMULATOR[/bold underline yellow]")
        
        # Show list of students
        for idx, student in enumerate(self.students):
            self.console.print(f"[{idx + 1}] {student['name']} (Class {student['class_level']} | Targets: {', '.join(student['targets'])})")
            
        stu_choice = Prompt.ask("\nSelect student to simulate pivots", default="1")
        if not stu_choice.isdigit() or not (1 <= int(stu_choice) <= len(self.students)):
            self.press_enter_to_continue("Invalid student selection.")
            return

        student = self.students[int(stu_choice) - 1]
        
        # Get baseline subjects
        current_subjects = list(student.get("board_subjects", []))
        self.console.print(f"\nSelected Student: [bold green]{student['name']}[/bold green]")
        self.console.print(f"Current Board Subjects: [cyan]{', '.join(current_subjects)}[/cyan]")
        
        self.console.print("\n[bold yellow]Enter simulated board subjects list (comma-separated):[/bold yellow]")
        self.console.print("e.g. Adding 'Mathematics' or switching 'Biology' to 'Applied Mathematics'")
        subjects_input = Prompt.ask("Simulated board subjects list", default=", ".join(current_subjects))
        
        simulated_list = [s.strip() for s in subjects_input.split(",") if s.strip()]
        
        # Run compliance reasoner on simulated subjects
        sim_analysis = self.reasoner.evaluate_student(student, simulated_subjects=simulated_list)
        
        # Show comparison
        self.inspect_student(student, sim_analysis, simulated_subjects=simulated_list)

    def export_report(self, analysis_results):
        """Exports full report as JSON to the project root directory."""
        export_data = {
            "timestamp": datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "system": "PRISM Co-pilot Fact Engine",
            "students": self.students,
            "audit_results": analysis_results
        }
        
        base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        export_path = os.path.join(base_dir, "prism_audit_report.json")
        
        with open(export_path, "w") as f:
            json.dump(export_data, f, indent=2)
            
        self.console.print(f"\n[bold green]✔ Compliance report successfully exported to:[/bold green]")
        self.console.print(f"[cyan]{export_path}[/cyan]")
        self.console.print("[dim]This JSON structure is ready to be parsed by your web frontend![/dim]")
        
        self.press_enter_to_continue()

    def press_enter_to_continue(self, msg=""):
        if msg:
            self.console.print(f"\n[bold yellow]{msg}[/bold yellow]")
        Prompt.ask("\nPress Enter to return to Dashboard")
