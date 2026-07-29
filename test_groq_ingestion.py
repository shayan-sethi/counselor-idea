import os
from prism_agent.ingestion_agent import DocumentIngestionAgent

sample_resume = """
Name: Rahul Sethi
Class: Grade 12 IBDP Student
Board: IB Diploma Programme
Subjects: HL Physics, HL Chemistry, HL Mathematics Analysis and Approaches, SL English Literature, SL Economics, SL Spanish B
Expected Board Score: 42/45
SAT Score: 1540
Grade 10 Board: IGCSE Cambridge
Grade 10 Marks: Physics: A*, Chemistry: A*, Math: A*, English: A, History: A, Economics: A*

Extracurriculars & Portfolio:
- Founded EpiAlert (Tier 1): AI-based disease surveillance app with 5,000+ users across India.
- School Football Team Captain (Tier 3): Led team to regional semi-finals.
- Robotics Competition Winner (Tier 2): 1st place in National STEM Challenge.

Target Universities: STANFORD_CS, MIT_STEM, CAMBRIDGE_CS
"""

def main():
    agent = DocumentIngestionAgent()
    print("[+] Ingesting sample document using Groq (llama-3.3-70b-versatile)...")
    res = agent.process_documents([sample_resume], ["rahul_resume.txt"])
    print("[+] Extraction Output Result:")
    import json
    print(json.dumps(res, indent=2))

if __name__ == "__main__":
    main()
