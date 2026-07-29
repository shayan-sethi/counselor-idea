import os
import json
import datetime
import google.generativeai as genai

class ScholarshipAgent:
    @staticmethod
    def match_scholarships(student, scholarships, silent=False):
        """
        Evaluates a student against all scholarships.
        Returns a list of matched scholarships with LLM-generated explanations.
        """
        student_id = student.get("id")
        student_name = student.get("name", "Student")
        class_level = int(student.get("class_level", 12))
        
        # Pre-filter scholarships based on basic constraints
        candidate_scholarships = []
        for schol in scholarships:
            min_c = schol.get("min_class_level", 9)
            max_c = schol.get("max_class_level", 12)
            if min_c <= class_level <= max_c:
                candidate_scholarships.append(schol)

        if not candidate_scholarships:
            return []

        # If API key is available, use Gemini for agentic reasoning
        api_key = os.environ.get("GEMINI_API_KEY", "")
        if api_key:
            return ScholarshipAgent._match_with_llm(student, candidate_scholarships, api_key, silent)
        else:
            return ScholarshipAgent._match_fallback(student, candidate_scholarships, silent)

    @staticmethod
    def _match_with_llm(student, candidate_scholarships, api_key, silent=False):
        genai.configure(api_key=api_key)
        
        prompt = f"""You are an expert Scholarship and Financial Aid Agent.
You will evaluate the eligibility and fit of {len(candidate_scholarships)} scholarship(s) for the following student profile:

Student Profile:
{json.dumps(student, indent=2)}

Available Scholarships:
{json.dumps(candidate_scholarships, indent=2)}

For EACH scholarship in the list, evaluate if the student is a fit based on their academics, targets, portfolio, and demographics.
Consider their expected board grades, SAT score, subjects, and intended targets. If the scholarship is need-based, evaluate based on the fact that need-based aid is available unless stated otherwise. 
Assign a match score from 0 to 100.
Also, provide an explanation ("why") and actionable steps ("actions_needed") to maximize their chances.

Return a JSON array of objects, one for each evaluated scholarship. Your entire response must be valid JSON matching this exact structure:
[
  {{
    "scholarship_id": "schol_tata_cornell",
    "match_score": 85,
    "why": "You are eligible for the Tata Scholarship because you are an Indian citizen targeting US universities...",
    "actions_needed": "Submit your CSS profile by the deadline and ensure your financial documents are translated.",
    "is_urgent": false,
    "days_remaining": 45
  }},
  ...
]
"""
        
        models_to_try = ["gemini-3.6-flash", "gemini-2.5-flash", "gemini-2.0-flash", "gemini-flash-latest"]
        last_error = None
        for model_name in models_to_try:
            try:
                model = genai.GenerativeModel(
                    model_name=model_name,
                    generation_config={"temperature": 0.1}
                )
                response = model.generate_content(prompt)
                final_text = response.text
                
                import re
                json_match = re.search(r"\[.*\]", final_text, re.DOTALL)
                if json_match:
                    matches_data = json.loads(json_match.group(0))
                else:
                    matches_data = json.loads(final_text)
                    
                # Merge with scholarship details
                results = []
                for m in matches_data:
                    schol_id = m.get("scholarship_id")
                    schol = next((s for s in candidate_scholarships if s["id"] == schol_id), None)
                    if schol:
                        m["scholarship"] = schol
                        results.append(m)
                        
                # Sort by match score descending
                results.sort(key=lambda x: x.get("match_score", 0), reverse=True)
                return results
                
            except Exception as e:
                last_error = e
                if not silent:
                    print(f"[ScholarshipAgent Warning] Model {model_name} failed: {e}. Trying next model...")

        if not silent:
            print(f"[ScholarshipAgent Error] All LLM models failed. Last error: {last_error}")
        return ScholarshipAgent._match_fallback(student, candidate_scholarships, silent)

    @staticmethod
    def _match_fallback(student, candidate_scholarships, silent=False):
        results = []
        for schol in candidate_scholarships:
            # Dummy fallback logic
            results.append({
                "scholarship_id": schol["id"],
                "scholarship": schol,
                "match_score": 70,
                "why": "This is a mock response because the LLM failed or API key was missing. The scholarship fits your basic profile.",
                "actions_needed": "Review the criteria on the official website.",
                "is_urgent": False,
                "days_remaining": 30
            })
        results.sort(key=lambda x: x.get("match_score", 0), reverse=True)
        return results

    @staticmethod
    def recommend_students(scholarship, all_students):
        """
        Uses Gemini to recommend the top 3 best-fit students for a given scholarship.
        """
        api_key = os.environ.get("GEMINI_API_KEY", "")
        if not api_key:
            # Fallback if no API key
            return [{"student_id": s["id"], "score": 50, "reason": "No API key provided."} for s in all_students[:3]]

        genai.configure(api_key=api_key)
        
        # Minify student profiles to save context window
        min_students = []
        for s in all_students:
            min_students.append({
                "id": s.get("id"),
                "name": s.get("name"),
                "class_level": s.get("class_level"),
                "expected_sat": s.get("expected_sat"),
                "subjects": s.get("board_subjects", []),
                "targets": [t.get("name") for t in s.get("target_pathways", [])],
                "financial_need": s.get("financial_need", "Unknown")
            })

        prompt = f"""You are an expert Scholarship Matching Agent.
I will give you a specific scholarship and a list of students.
Please return the top 3 best fit students for this scholarship.

Scholarship:
{json.dumps(scholarship, indent=2)}

Students:
{json.dumps(min_students, indent=2)}

For the top 3 matching students, assign a score out of 100 and write a 1-2 sentence reason why they are a great fit.

Respond strictly with a JSON array in this format:
[
  {{
    "student_id": "stu_...",
    "score": 95,
    "reason": "..."
  }}
]
"""
        models_to_try = ["gemini-3.6-flash", "gemini-2.5-flash", "gemini-2.0-flash", "gemini-flash-latest"]
        last_error = None
        for model_name in models_to_try:
            try:
                model = genai.GenerativeModel(model_name)
                response = model.generate_content(prompt)
                text = response.text
                start = text.find('[')
                end = text.rfind(']') + 1
                if start != -1 and end != 0:
                    text = text[start:end]
                return json.loads(text)
            except Exception as e:
                last_error = e
                print(f"[ScholarshipAgent recommend_students Warning] Model {model_name} failed: {e}. Trying next model...")

        print(f"[ScholarshipAgent recommend_students Error] All models failed. Last error: {last_error}")
        return [{"student_id": s["id"], "score": 50, "reason": f"Fallback due to LLM error: {last_error}"} for s in all_students[:3]]
