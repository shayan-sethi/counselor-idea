import os
import json
import time
import datetime

from .groq_utils import get_groq_api_keys, groq_post_with_retry, GROQ_MODEL


def _groq_post_with_retry(groq_key, payload, label="Groq", max_wait=15):
    return groq_post_with_retry(payload, label=label, max_wait=max_wait, initial_key=groq_key)


COLLEGE_NAME_MAP = {
    "UK_THELONDONSCHOOLOFECONOMICSANDPOLITICALSCIENCE": "London School of Economics (LSE)",
    "LSE": "London School of Economics (LSE)",
    "LSE Economics": "London School of Economics (LSE)",
    "UK_OXFORDBROOKESUNIVERSITY": "Oxford Brookes University",
    "UK_UNIVERSITYOFOXFORD": "University of Oxford",
    "OXFORD": "University of Oxford",
    "UK_UNIVERSITYOFCAMBRIDGE": "University of Cambridge",
    "CAMBRIDGE": "University of Cambridge",
    "US_STANFORDUNIVERSITY": "Stanford University",
    "STANFORD": "Stanford University",
    "US_MASSACHUSETTSINSTITUTEOFTECHNOLOGY": "Massachusetts Institute of Technology (MIT)",
    "MIT": "MIT",
    "ASHOKA_UNIV": "Ashoka University",
    "ASHOKA": "Ashoka University",
    "DU": "Delhi University",
    "DELHI_UNIV": "Delhi University",
    "UCL": "University College London (UCL)",
    "UK_UNIVERSITYCOLLEGELONDON": "University College London (UCL)",
    "HARVARD": "Harvard University",
    "US_HARVARDUNIVERSITY": "Harvard University",
    "PRINCETON": "Princeton University",
    "YALE": "Yale University",
    "COLUMBIA": "Columbia University",
    "CORNELL": "Cornell University",
    "UPENN": "University of Pennsylvania",
    "BROWN": "Brown University",
    "DARTMOUTH": "Dartmouth College",
    "AIIMS": "AIIMS",
    "IIT_BOMBAY": "IIT Bombay",
    "BITS_PILANI": "BITS Pilani",
    "VIT": "VIT Vellore",
    "KING'S_COLLEGE_LONDON": "King's College London",
    "US_166027": "Harvard University",
}

def clean_university_name(s):
    if not s or not isinstance(s, str):
        return str(s) if s else ""
    s_trim = s.strip()
    if s_trim in COLLEGE_NAME_MAP:
        return COLLEGE_NAME_MAP[s_trim]
    if s_trim.startswith("UK_") or s_trim.startswith("US_") or s_trim.startswith("IND_"):
        raw = s_trim.split("_", 1)[1]
        if "LONDONSCHOOLOFECONOMICS" in raw:
            return "London School of Economics (LSE)"
        if "OXFORDBROOKES" in raw:
            return "Oxford Brookes University"
        if "OXFORD" in raw:
            return "University of Oxford"
        if "CAMBRIDGE" in raw:
            return "University of Cambridge"
        if "STANFORD" in raw:
            return "Stanford University"
        if "MASSACHUSETTS" in raw or "MIT" in raw:
            return "MIT"
        if "HARVARD" in raw:
            return "Harvard University"
        if "PRINCETON" in raw:
            return "Princeton University"
        if "YALE" in raw:
            return "Yale University"
        if "COLUMBIA" in raw:
            return "Columbia University"
        if "CORNELL" in raw:
            return "Cornell University"
        if "IMPERIAL" in raw:
            return "Imperial College London"
        if "UNIVERSITYCOLLEGELONDON" in raw or "UCL" in raw:
            return "University College London (UCL)"
        return raw.title().replace("Of", "of").replace("And", "and")
    return s_trim


class ScholarshipAgent:

    @staticmethod
    def match_scholarships(student, scholarships, silent=False):
        """
        Evaluates a student against all scholarships using Groq API.
        Retries for up to ~15 s on rate-limit before falling back.
        """
        class_level = int(student.get("class_level", 12))
        candidate_scholarships = [
            s for s in scholarships
            if s.get("min_class_level", 9) <= class_level <= s.get("max_class_level", 12)
        ]
        if not candidate_scholarships:
            return []

        if get_groq_api_keys():
            result = ScholarshipAgent._match_with_groq(student, candidate_scholarships, None, silent)
            if result is not None:
                return result

        if not silent:
            print("[ScholarshipAgent] All Groq retries exhausted — returning error response")
        return ScholarshipAgent._match_error(student, candidate_scholarships)

    @staticmethod
    def _match_with_groq(student, candidate_scholarships, groq_key, silent=False):
        grade = student.get("grades", {}).get("current_expected_board", "N/A")
        tests = student.get("standardized_tests", {})
        subjects = student.get("board_subjects", [])

        schol_brief = [{"id": s["id"], "name": s.get("name",""), "criteria": s.get("eligibility_criteria",""), "amount": s.get("amount",""), "deadline": s.get("deadline","")} for s in candidate_scholarships]

        prompt = f"""Score scholarship fit. Return JSON array.

Student: grade={grade}, board={student.get("board")}, SAT={tests.get("SAT","N/A")}, subjects={subjects[:6]}

Scholarships: {json.dumps(schol_brief)}

[{{"scholarship_id":"<id>","match_score":<0-100>,"why":"<1 line>","actions_needed":"<1 line>","is_urgent":false,"days_remaining":<int>}}]"""
        payload = {
            "model": GROQ_MODEL,
            "messages": [
                {"role": "system", "content": "Return ONLY valid JSON."},
                {"role": "user",   "content": prompt},
            ],
            "response_format": {"type": "json_object"},
            "temperature": 0.1,
            "max_tokens": 400,
        }

        res, err = _groq_post_with_retry(groq_key, payload, label="ScholarshipAgent.match")
        if res is None:
            return None

        try:
            raw = res.json()["choices"][0]["message"]["content"]
            matches_data = json.loads(raw)

            # Unwrap common wrapper keys
            if isinstance(matches_data, dict):
                for k in ["scholarships", "evaluated_scholarships", "recommendations", "data", "matches", "results"]:
                    if k in matches_data and isinstance(matches_data[k], list):
                        matches_data = matches_data[k]
                        break
                if isinstance(matches_data, dict):
                    arr = next((v for v in matches_data.values() if isinstance(v, list)), None)
                    if arr:
                        matches_data = arr

            if not isinstance(matches_data, list):
                return None

            results = []
            for m in matches_data:
                schol_id = m.get("scholarship_id") or m.get("id")
                schol = next((s for s in candidate_scholarships if s["id"] == schol_id), None)
                if not schol:
                    schol = candidate_scholarships[0]
                m["scholarship"] = schol
                results.append(m)
            results.sort(key=lambda x: x.get("match_score", 0), reverse=True)
            return results

        except Exception as parse_err:
            print(f"[ScholarshipAgent.match] JSON parse error: {parse_err}")
            return None

    @staticmethod
    def _match_error(student, candidate_scholarships):
        """Returned only when Groq is completely unreachable — makes the error visible."""
        return [{
            "scholarship_id": s["id"],
            "scholarship": s,
            "match_score": 0,
            "why": "• AI matching unavailable — Groq API rate limit or connection error.\\n• Please wait a moment and click Find Best Matches again.",
            "actions_needed": "• Retry in 30 seconds.\\n• Contact support if this persists.",
            "is_urgent": False,
            "days_remaining": None,
        } for s in candidate_scholarships]

    # ─────────────────────────────────────────────────────────────────
    #  RECOMMEND STUDENTS (counselor view → "Find Best Matches" button)
    # ─────────────────────────────────────────────────────────────────

    @staticmethod
    def recommend_students(scholarship, all_students):
        """
        Uses Groq API to recommend top 3 best-fit students for a scholarship.
        Retries for up to ~15 s on rate-limit before falling back.
        """
        brief_students = [{"id": s.get("id"), "name": s.get("name"), "board": s.get("board"), "grade": s.get("grades",{}).get("current_expected_board","N/A"), "SAT": s.get("standardized_tests",{}).get("SAT","N/A"), "subjects": s.get("board_subjects",[])[:5]} for s in all_students]

        prompt = f"""Pick top 3 students for this scholarship. Return JSON.

Scholarship: {scholarship.get("name","")}, criteria={scholarship.get("eligibility_criteria","")}, amount={scholarship.get("amount","")}

Students: {json.dumps(brief_students)}

{{"recommendations":[{{"student_id":"<id>","score":<0-100>,"reason":"<1 sentence>"}}]}}"""
        payload = {
            "model": GROQ_MODEL,
            "messages": [
                {"role": "system", "content": "Return ONLY valid JSON."},
                {"role": "user",   "content": prompt},
            ],
            "response_format": {"type": "json_object"},
            "temperature": 0.15,
            "max_tokens": 300,
        }

        if get_groq_api_keys():
            res, err = _groq_post_with_retry(None, payload, label="ScholarshipAgent.recommend")
            if res is not None:
                try:
                    data = json.loads(res.json()["choices"][0]["message"]["content"])
                    if isinstance(data, dict):
                        for k in ["recommendations", "students", "data"]:
                            if k in data and isinstance(data[k], list):
                                return data[k]
                        arr = next((v for v in data.values() if isinstance(v, list)), None)
                        if arr:
                            return arr
                    elif isinstance(data, list):
                        return data
                except Exception as parse_err:
                    print(f"[ScholarshipAgent.recommend] JSON parse error: {parse_err}")
            else:
                print(f"[ScholarshipAgent.recommend] All retries failed: {err}")

        # True last-resort fallback — labelled as an error, not fake AI output
        return [{
            "student_id": s.get("id"),
            "score": 0,
            "reason": f"• AI matching unavailable — Groq API unreachable.\\n• Please retry in 30 seconds.",
        } for s in all_students[:3]]

