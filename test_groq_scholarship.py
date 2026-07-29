import json
try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass
from prism_agent.scholarship_agent import ScholarshipAgent

def test_scholarship_reco():
    schol = {
        "id": "schol_tata_cornell",
        "name": "Tata Scholarship for Cornell University",
        "type": "Need-based",
        "provider": "Tata Education and Development Trust",
        "eligibility_criteria": "Indian citizens admitted to undergraduate programs at Cornell University.",
        "award_value": "Full Tuition",
        "deadline": "2026-11-01",
        "tags": ["Need-based", "US", "Engineering", "Computer Science"],
        "min_class_level": 12,
        "max_class_level": 12
    }

    students = [
        {"id": "STU_001", "name": "Rahul Sethi", "class_level": 12, "expected_sat": 1540, "board_subjects": ["Physics", "Math"], "target_pathways": ["STANFORD_CS"], "financial_need": "High"},
        {"id": "STU_002", "name": "Ananya Roy", "class_level": 12, "expected_sat": 1490, "board_subjects": ["Biology", "Chemistry"], "target_pathways": ["CORNELL_BIO"], "financial_need": "High"}
    ]

    print("[+] Testing Scholarship Student Recommendation via Groq...")
    reco = ScholarshipAgent.recommend_students(schol, students)
    print("[+] Result:")
    print(json.dumps(reco, indent=2))

if __name__ == "__main__":
    test_scholarship_reco()
