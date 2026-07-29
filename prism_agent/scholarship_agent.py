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
        api_key = osiron.get("GEMINI_API_KEY", "")
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
        
        try:
            model = genai.GenerativeModel(
                model_name="gemini-2.0-flash",
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
            if not silent:
                print(f"[ScholarshipAgent Error] {e}")
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
