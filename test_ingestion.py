import sys
import json
from prism_agent.ingestion_agent import DocumentIngestionAgent

def run_test():
    print("====================================================")
    print("PRISM AUTOMATED INGESTION AGENT TEST")
    print("====================================================")

    agent = DocumentIngestionAgent()

    sample_transcript = """
    OFFICIAL ACADEMIC TRANSCRIPT
    Student Name: Vikram Malhotra
    Grade / Class: Class 12
    Board: CBSE
    Academic Year: 2025-2026

    SUBJECTWISE MARKS:
    1. Mathematics: 96%
    2. Physics: 94%
    3. Chemistry: 92%
    4. Computer Science: 98%
    5. English Core: 91%

    Overall Aggregate: 94.2%
    SAT Score: 1540
    """

    sample_resume = """
    VIKRAM MALHOTRA - RESUME & PORTFOLIO
    Email: vikram@example.com

    EXTRACURRICULAR ACTIVITIES & HONORS:
    - Winner, National Science Olympiad 2025: Awarded Gold Medal among 50,000 participants nationwide.
    - President, Computer Science Club: Led a team of 30 students and organized state-level hackathon.
    - IMO Qualifier: Passed regional mathematics olympiad.
    """

    print("Processing sample transcript & resume...")
    result = agent.process_documents([sample_transcript, sample_resume], ["transcript.txt", "resume.txt"])

    print("\n--- Extracted Profile Output ---")
    print(json.dumps(result, indent=2))

    # Assertions
    failures = 0
    if "Vikram" in result.get("name", ""):
        print("[✔] Correctly extracted student name.")
    else:
        print(f"[❌] Failed to extract name: {result.get('name')}")
        failures += 1

    if result.get("board") == "CBSE":
        print("[✔] Correctly identified CBSE board.")
    else:
        print(f"[❌] Board mismatch: {result.get('board')}")
        failures += 1

    if result.get("standardized_tests", {}).get("SAT") == 1540:
        print("[✔] Correctly extracted SAT score (1540).")
    else:
        print(f"[❌] SAT score mismatch: {result.get('standardized_tests')}")
        failures += 1

    if len(result.get("portfolio", [])) > 0:
        print(f"[✔] Correctly extracted {len(result['portfolio'])} portfolio activities with impact tiers.")
    else:
        print("[❌] Failed to extract portfolio items.")
        failures += 1

    print("\n====================================================")
    if failures == 0:
        print("[✔] ALL INGESTION TESTS PASSED SUCCESSFULLY!")
        sys.exit(0)
    else:
        print(f"[❌] TEST FAILED WITH {failures} ERRORS.")
        sys.exit(1)

if __name__ == "__main__":
    run_test()
