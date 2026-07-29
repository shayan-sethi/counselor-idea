import os
import json
import time
import datetime

GROQ_ENDPOINT = "https://api.groq.com/openai/v1/chat/completions"
GROQ_MODEL    = "llama-3.3-70b-versatile"

def _groq_post_with_retry(groq_key, payload, label="Groq", max_wait=15):
    """
    POST to Groq with exponential-backoff retries for up to `max_wait` seconds.
    Returns (response_object | None, error_string | None)
    """
    import requests
    delays = [3]              # 1 retry after 3 s — cache handles repeated clicks
    deadline = time.time() + max_wait
    last_err = "unknown"

    for attempt, delay in enumerate(delays + [0], start=1):
        try:
            print(f"[{label}] attempt {attempt} …")
            res = requests.post(
                GROQ_ENDPOINT,
                headers={"Authorization": f"Bearer {groq_key}", "Content-Type": "application/json"},
                json=payload,
                timeout=30,
            )
            if res.status_code == 200:
                return res, None
            elif res.status_code in (429, 503):
                last_err = f"HTTP {res.status_code} (rate-limit / overload)"
                print(f"[{label}] {last_err} — waiting {delay}s before retry …")
            else:
                last_err = f"HTTP {res.status_code}: {res.text[:200]}"
                print(f"[{label}] non-retryable error: {last_err}")
                return None, last_err
        except Exception as exc:
            last_err = str(exc)
            print(f"[{label}] request exception: {last_err}")

        if time.time() + delay > deadline or delay == 0:
            break
        time.sleep(delay)

    return None, last_err


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

        groq_key = os.environ.get("GROQ_API_KEY", "").strip()
        if groq_key:
            result = ScholarshipAgent._match_with_groq(student, candidate_scholarships, groq_key, silent)
            if result is not None:
                return result

        if not silent:
            print("[ScholarshipAgent] All Groq retries exhausted — returning error response")
        return ScholarshipAgent._match_error(student, candidate_scholarships)

    @staticmethod
    def _match_with_groq(student, candidate_scholarships, groq_key, silent=False):
        prompt = f"""You are an expert Scholarship and Financial Aid Agent for unlockED.
Evaluate the eligibility and strategic fit of {len(candidate_scholarships)} scholarship(s) for the following student profile:

Student Profile:
{json.dumps(student, indent=2)}

Available Scholarships:
{json.dumps(candidate_scholarships, indent=2)}

For EACH scholarship, assign a match score 0-100 and write EXACTLY 2 short bullet lines (max 15-20 words each) for "why" and "actions_needed". Separate the two bullets with a literal \\n.

Return a valid JSON array:
[
  {{
    "scholarship_id": "schol_tata_cornell",
    "match_score": 88,
    "why": "• 1540 SAT & 42/45 IB score meets STEM threshold.\\n• Cornell target pathway aligns with scholarship focus.",
    "actions_needed": "• Submit CSS Profile before Nov 1st deadline.\\n• Get financial counselor sign-off.",
    "is_urgent": false,
    "days_remaining": 45
  }}
]
"""
        payload = {
            "model": GROQ_MODEL,
            "messages": [
                {"role": "system", "content": "You are unlockED Scholarship AI. Return ONLY a valid JSON array of scholarship match objects."},
                {"role": "user",   "content": prompt},
            ],
            "response_format": {"type": "json_object"},
            "temperature": 0.1,
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
        groq_key = os.environ.get("GROQ_API_KEY", "").strip()

        rich_students = []
        for s in all_students:
            rich_students.append({
                "id":                s.get("id"),
                "name":              s.get("name"),
                "class_level":       s.get("class_level"),
                "board":             s.get("board"),
                "expected_grade":    s.get("grades", {}).get("current_expected_board", "N/A"),
                "standardized_tests": s.get("standardized_tests", {}),
                "board_subjects":    s.get("board_subjects", []),
                "targets":           [t.get("name") if isinstance(t, dict) else str(t) for t in s.get("target_pathways", [])],
                "portfolio_summary": [p.get("activity") if isinstance(p, dict) else str(p) for p in s.get("portfolio", [])],
                "financial_need":    s.get("financial_need", "High"),
            })

        prompt = f"""You are an expert Chief Admissions Officer & Financial Aid Counselor for unlockED.
Analyze this scholarship and evaluate the student roster. Select the top 3 best-fit students.

Scholarship:
{json.dumps(scholarship, indent=2)}

Candidate Roster:
{json.dumps(rich_students, indent=2)}

For each of the top 3, write EXACTLY 2 short bullet lines (max 15-20 words each). No long paragraphs.
Example:
"• 96% IB score & 1540 SAT matches STEM criteria.\\n• Rural Book Service leadership shows community alignment."

Return a JSON object:
{{
  "recommendations": [
    {{
      "student_id": "STU_001",
      "score": 96,
      "reason": "• 42/45 IB score & 1540 SAT matches STEM criteria.\\n• EpiAlert project aligns with Tata innovation focus."
    }}
  ]
}}
"""
        payload = {
            "model": GROQ_MODEL,
            "messages": [
                {"role": "system", "content": "You are unlockED Scholarship Matching Agent. Return ONLY a valid JSON object."},
                {"role": "user",   "content": prompt},
            ],
            "response_format": {"type": "json_object"},
            "temperature": 0.15,
        }

        if groq_key:
            res, err = _groq_post_with_retry(groq_key, payload, label="ScholarshipAgent.recommend")
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

