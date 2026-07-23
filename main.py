import sys
import argparse
import json
import os
from prism_agent.counselor_dashboard import CounselorDashboard

def main():
    parser = argparse.ArgumentParser(
        description="PRISM: Prerequisite & Risk Intervention System for Matriculation (Counselor Co-pilot)"
    )
    parser.add_argument(
        "--export", 
        action="store_true", 
        help="Run headless audit, export results to 'prism_audit_report.json' and exit immediately."
    )
    
    args = parser.parse_args()

    # Initialize dashboard co-pilot
    try:
        dashboard = CounselorDashboard()
    except Exception as e:
        print(f"Error initializing PRISM co-pilot: {e}", file=sys.stderr)
        sys.exit(1)

    if args.export:
        print("Running headless compliance audit on cohort...")
        analysis_results = dashboard.reasoner.evaluate_cohort(dashboard.students)
        
        export_data = {
            "timestamp": os.popen("date").read().strip(),
            "system": "PRISM Co-pilot Headless Fact Engine",
            "students": dashboard.students,
            "audit_results": analysis_results
        }
        
        base_dir = os.path.dirname(os.path.abspath(__file__))
        export_path = os.path.join(base_dir, "prism_audit_report.json")
        
        with open(export_path, "w") as f:
            json.dump(export_data, f, indent=2)
            
        print(f"✔ Audit complete. Report exported successfully to: {export_path}")
        sys.exit(0)
    else:
        # Start interactive terminal dashboard
        dashboard.run()

if __name__ == "__main__":
    main()
