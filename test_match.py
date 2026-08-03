import os
import json
from prism_agent.scholarship_agent import ScholarshipAgent
import server

scholarships = server.load_scholarships()
schol = next((s for s in scholarships if s["id"] == "schol_tata_cornell"), None)
students = server.load_students()

print("Testing recommend_students...")
res = ScholarshipAgent.recommend_students(schol, students)
print("Result:")
print(json.dumps(res, indent=2))
