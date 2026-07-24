from prism_agent.ingestion_agent import DocumentIngestionAgent
import json

full_user_resume = """
Saiansh Tapuriah
Email: saiansh@example.com | Phone: +91 9876543210

Education:
IB Diploma Programme (Currently Pursuing), Grade 11
o Higher Level (HL): Physics, Chemistry, Economics, Mathematics AA
o Standard Level (SL): English, Spanish

• Previously completed IGCSE (Grades 6–10)
o Consistent Grade Topper across all academic years
o Achieved 9A* in IGCSE Board Examinations (Feb-March 2026) in:
▪ First Language English
▪ Literature in English
▪ Physics
▪ Chemistry
▪ Computer Science
▪ Mathematics International
▪ Geography
▪ Environmental Management
▪ Spanish

• Standardised Testing:
o SAT: 1570 (790 Maths, 780 English RW) – May 2026

INITIATIVES/PROJECTS
EpiAlert EpiAlert is an innovative device developed by Saiansh, that can detect Epileptic seizures and raise alarms, enabling immediate care for the patient. No such device exists in India. (Patent applied for)
Device has been recognized nationally, with the Dr. APJ Abdul Kalam Ignited Mind Award and the Best Prototype award at Plaksha University’s Young Creator’s League.
Media coverage: https://www.thehindu.com/news/cities/Delhi/gurugram-student-wins-apj-abdul-kalam-ignited-minds-children-creativity-and-innovation-award-2023-24/article68451463.ece

Pollution Alert
To reduce the widespread air pollution in the city, Saiansh developed a mobile application that can be used to report instances of air pollution along with their location to government authorities. The government has acted on various reports of pollution via the app.
The app has been recognised by Google and Times of India.

INTERESTS
• Technology: Python programming, ML development, avid tech quizzer
• Sports: Swimmer with medals at the national level, represented the country at ISF World School Games
• Science: Interested in Physics advancements and research, worked as part of winning team at the Asian Regional Space Settlement Design Competition (aerospace engineering simulation)
• Maths: UKMT Senior Mathematics Competition Gold Award, Cathedral Maths Competition Gold Award
• Scuba Diving: interested in aquatic exploration and wildlife photography
"""

def test_full_resume():
    print("====================================================")
    print("TESTING FULL USER RESUME WITH INITIATIVES & INTERESTS")
    print("====================================================")

    agent = DocumentIngestionAgent()
    result = agent.process_documents([full_user_resume], ["resume.pdf"])

    print("\nPARSED PORTFOLIO ITEMS (INITIATIVES, PROJECTS, INTERESTS):")
    for idx, item in enumerate(result["portfolio"], 1):
        print(f"{idx}. [Tier {item['tier']}] {item['activity']}")
        print(f"   Description: {item['description']}\n")

    print(f"Total Portfolio Items Extracted: {len(result['portfolio'])}")

    # Assertions
    assert len(result["portfolio"]) >= 5, f"Expected at least 5 EC/Initiative items, got {len(result['portfolio'])}"
    
    activities_str = " ".join([i["description"] for i in result["portfolio"]]).lower()
    assert "epialert" in activities_str or "patent" in activities_str, "Missing EpiAlert project"
    assert "pollution alert" in activities_str or "google" in activities_str, "Missing Pollution Alert project"
    assert "swimmer" in activities_str or "isf world school games" in activities_str, "Missing Sports/Swimming interest"
    assert "ukmt" in activities_str or "cathedral" in activities_str, "Missing Maths UKMT Gold Award"
    assert "space settlement" in activities_str or "asian regional" in activities_str, "Missing Asian Regional Space Settlement Competition"

    print("\n====================================================")
    print("[SUCCESS] ALL INITIATIVES, PROJECTS & INTERESTS EXTRACTED 100%!")
    print("====================================================")

if __name__ == "__main__":
    test_full_resume()
