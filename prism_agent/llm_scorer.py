import os
import json
import time
import requests
import datetime

GROQ_ENDPOINT = "https://api.groq.com/openai/v1/chat/completions"
GROQ_MODEL = "llama-3.3-70b-versatile"

ELITE_KEYWORDS = [
    "cambridge", "oxford", "mit", "stanford", "harvard", "yale", "princeton",
    "caltech", "imperial", "iit bombay", "iit delhi", "iit madras", "aiims",
    "columbia", "chicago", "iisc",
]

HARD_BLOCK_TYPES = {"subject_missing", "cuet_missing_subject", "cuet_unlawful_domain"}


def _groq_post_with_retry(groq_key, payload, label="Groq", max_wait=15):
    delays = [3]
    deadline = time.time() + max_wait
    last_err = "unknown"

    for attempt, delay in enumerate(delays + [0], start=1):
        try:
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
            else:
                last_err = f"HTTP {res.status_code}: {res.text[:200]}"
                return None, last_err
        except Exception as exc:
            last_err = str(exc)

        if time.time() + delay > deadline or delay == 0:
            break
        time.sleep(delay)

    return None, last_err


class LLMScorer:

    def __init__(self):
        self._cache = {}
        self._cache_ttl = 300

    # ── Cache helpers ────────────────────────────────────────────────────

    def _cache_key(self, prefix, *parts):
        return f"{prefix}:{'|'.join(str(p) for p in parts)}"

    def _get_cached(self, key):
        if key in self._cache:
            result, ts = self._cache[key]
            if time.time() - ts < self._cache_ttl:
                return result
            del self._cache[key]
        return None

    def _set_cached(self, key, result):
        self._cache[key] = (result, time.time())

    # ── Post-LLM safety gates ────────────────────────────────────────────

    def validate_and_enforce(self, result, target, gaps):
        score = result.get("match_score", 50)
        difficulty = result.get("difficulty_label", result.get("difficulty", "Target"))

        has_hard_block = any(
            g.get("type") in HARD_BLOCK_TYPES and g.get("severity") == "CRITICAL"
            for g in gaps
        )
        if has_hard_block:
            score = min(score, 35)
            difficulty = "Reach"

        admission_tests = target.get("admission_tests", []) if target else []
        cuet_jee_required = any(
            t in ("CUET_UG", "JEE_MAIN", "JEE Mains", "JEE_ADVANCED")
            for t in admission_tests
        )
        if cuet_jee_required and difficulty == "Safety":
            difficulty = "Target"

        uni_name = (target.get("university", "") or target.get("name", "")).lower() if target else ""
        if any(kw in uni_name for kw in ELITE_KEYWORDS):
            score = min(score, 78)
            if difficulty == "Safety":
                difficulty = "Target"

        score = max(5, min(92, score))

        result["match_score"] = int(round(score))
        result["difficulty_label"] = difficulty
        if "difficulty" in result:
            result["difficulty"] = difficulty
        return result

    # ── 1. Score + classify a student-target pair ────────────────────────

    def score_and_classify(self, student, target, gaps, remediations=None):
        groq_key = os.environ.get("GROQ_API_KEY", "").strip()
        if not groq_key or not student or not target:
            return None

        ck = self._cache_key("score", student.get("id"), target.get("id", target.get("name")))
        cached = self._get_cached(ck)
        if cached:
            return cached

        admission_tests = target.get("admission_tests", [])
        student_summary = {
            "id": student.get("id"),
            "name": student.get("name"),
            "board": student.get("board"),
            "class_level": student.get("class_level"),
            "expected_grade": student.get("grades", {}).get("current_expected_board"),
            "board_subjects": student.get("board_subjects", []),
            "standardized_tests": student.get("standardized_tests", {}),
            "portfolio_count": len(student.get("portfolio", [])),
            "best_portfolio_tier": min([a.get("tier", 3) for a in student.get("portfolio", [])] or [4]),
        }

        prompt = f"""You are an expert college admissions evaluator. Given a student profile, target requirements, and compliance gaps, assign a match score and classify difficulty.

Student: {json.dumps(student_summary)}
Target: {json.dumps({"name": target.get("name"), "track": target.get("track"), "university": target.get("university"), "admission_tests": admission_tests, "portfolio_tier": target.get("portfolio_tier"), "grade_prerequisites": target.get("grade_prerequisites", [])})}
Compliance Gaps: {json.dumps(gaps)}
Remediations Available: {json.dumps(remediations or [])}

SCORING RULES (you MUST follow these):
1. match_score is 0-100. If ANY gap has severity "CRITICAL" and type "subject_missing", "cuet_missing_subject", or "cuet_unlawful_domain", score MUST be <= 35.
2. Super-selective institutions (Oxford, Cambridge, MIT, Stanford, Harvard, IITs, AIIMS) cap at 78 maximum.
3. No score above 92 regardless of strength.
4. risk_level: >=85 "Exceptional Match", 70-84 "Strong Match", 40-69 "Moderate Risk", <40 "Critical".

DIFFICULTY RULES:
1. If the target requires CUET_UG or JEE_MAIN or JEE_ADVANCED in admission_tests, it can NEVER be "Safety". These are competitive national exams with unpredictable outcomes.
2. Super-selective institutions are NEVER "Safety", at most "Target".
3. Any CRITICAL gap = "Reach".
4. "Safety" = high confidence of admission. "Target" = competitive but realistic. "Reach" = significant uncertainty or gaps.

Return ONLY valid JSON:
{{"match_score": <int>, "risk_level": "<label>", "difficulty_label": "<Safety|Target|Reach>", "scoring_rationale": "<2-3 sentences>"}}"""

        payload = {
            "model": GROQ_MODEL,
            "messages": [
                {"role": "system", "content": "You are unlockED AI Scoring Engine. Return ONLY valid JSON."},
                {"role": "user", "content": prompt},
            ],
            "response_format": {"type": "json_object"},
            "temperature": 0.1,
        }

        res, err = _groq_post_with_retry(groq_key, payload, label="LLMScorer.score")
        if res is None:
            return None

        try:
            data = json.loads(res.json()["choices"][0]["message"]["content"])
            data["match_score"] = int(data.get("match_score", 50))
            data = self.validate_and_enforce(data, target, gaps)
            self._set_cached(ck, data)
            return data
        except Exception:
            return None

    # ── 2. Classify a shortlisted college ────────────────────────────────

    def classify_shortlist(self, student, college):
        groq_key = os.environ.get("GROQ_API_KEY", "").strip()
        if not groq_key:
            return None

        college_name = college.get("name", "Unknown")
        ck = self._cache_key("shortlist", student.get("id"), college.get("id", college_name))
        cached = self._get_cached(ck)
        if cached:
            return cached

        grades_dict = student.get("grades", {})
        grade = grades_dict.get("current_expected_board") or grades_dict.get("class_12_aggregate") or grades_dict.get("class_10_aggregate") or "80"
        tests_dict = student.get("standardized_tests", {})
        sat = tests_dict.get("SAT") or tests_dict.get("sat") or 0

        portfolio = student.get("portfolio", [])
        best_tier = min([a.get("tier", 3) for a in portfolio] or [4])

        required_exams = college.get("admission_tests", college.get("required_exams", []))
        country = college.get("country", college.get("track", ""))

        prompt = f"""Classify this student's realistic admission chances at this college as "Safety", "Target", or "Reach".

Student:
- Expected Grade: {grade}
- SAT Score: {sat}
- Board: {student.get("board", "Unknown")}
- Best Portfolio Tier: {best_tier} (1=elite international, 2=regional/national, 3=school-level, 4=none)
- Board Subjects: {student.get("board_subjects", [])}

College: {college_name}
Country/Track: {country}
Required Exams: {json.dumps(required_exams)}

HARD RULES:
1. If the college requires CUET_UG or JEE_MAIN or JEE_ADVANCED, it can NEVER be "Safety". These competitive exams make outcomes unpredictable regardless of student strength.
2. Elite institutions (Harvard, MIT, Stanford, Oxford, Cambridge, IITs, AIIMS, Imperial, Caltech, Princeton, Yale, Columbia, Chicago) are NEVER "Safety".
3. Consider both academic fit AND exam requirements when classifying.

Return ONLY valid JSON: {{"category": "<Safety|Target|Reach>", "tier": <1-4>, "reasoning": "<1 sentence>"}}"""

        payload = {
            "model": GROQ_MODEL,
            "messages": [
                {"role": "system", "content": "You are unlockED AI Admissions Classifier. Return ONLY valid JSON."},
                {"role": "user", "content": prompt},
            ],
            "response_format": {"type": "json_object"},
            "temperature": 0.1,
        }

        res, err = _groq_post_with_retry(groq_key, payload, label="LLMScorer.shortlist")
        if res is None:
            return None

        try:
            data = json.loads(res.json()["choices"][0]["message"]["content"])
            category = data.get("category", "Target")
            tier = int(data.get("tier", 3))

            # Post-LLM CUET/JEE gate
            if any(t in ("CUET_UG", "JEE_MAIN", "JEE_ADVANCED", "JEE Mains") for t in required_exams):
                if category == "Safety":
                    category = "Target"

            name_lower = college_name.lower()
            if any(kw in name_lower for kw in ELITE_KEYWORDS) and category == "Safety":
                category = "Target"

            result = {"category": category, "tier": tier, "reasoning": data.get("reasoning", "")}
            self._set_cached(ck, result)
            return result
        except Exception:
            return None

    # ── 3. Score opportunities (batch) ───────────────────────────────────

    def score_opportunities(self, student, competitions):
        groq_key = os.environ.get("GROQ_API_KEY", "").strip()
        if not groq_key or not competitions:
            return None

        ck = self._cache_key("opps", student.get("id"), len(competitions))
        cached = self._get_cached(ck)
        if cached:
            return cached

        comp_summaries = []
        for c in competitions[:15]:
            comp_summaries.append({
                "id": c.get("id"),
                "name": c.get("name"),
                "subject_tags": c.get("subject_tags", []),
                "portfolio_tier": c.get("portfolio_tier", 3),
                "deadline": c.get("deadline"),
                "type": c.get("type", "Competition"),
            })

        student_summary = {
            "name": student.get("name"),
            "board_subjects": student.get("board_subjects", []),
            "targets": student.get("targets", []),
            "expected_grade": student.get("grades", {}).get("current_expected_board"),
            "portfolio": [a.get("activity") for a in student.get("portfolio", [])],
        }

        prompt = f"""You are an expert admissions opportunity matcher. Score how well each competition fits this student (0-100).

Student: {json.dumps(student_summary)}

Competitions:
{json.dumps(comp_summaries, indent=1)}

For EACH competition, consider:
- Subject alignment with student's board subjects
- Strategic value for the student's target university pathways
- Portfolio tier improvement potential
- Deadline feasibility

Return ONLY a valid JSON array (one entry per competition):
[{{"competition_id": "<id>", "match_score": <0-100>, "why": "<1-2 sentence explanation>", "is_urgent": <bool>}}]"""

        payload = {
            "model": GROQ_MODEL,
            "messages": [
                {"role": "system", "content": "You are unlockED Opportunity Radar AI. Return ONLY a valid JSON array."},
                {"role": "user", "content": prompt},
            ],
            "response_format": {"type": "json_object"},
            "temperature": 0.15,
        }

        res, err = _groq_post_with_retry(groq_key, payload, label="LLMScorer.opportunities")
        if res is None:
            return None

        try:
            raw = json.loads(res.json()["choices"][0]["message"]["content"])
            if isinstance(raw, dict):
                for k in ["opportunities", "competitions", "results", "data", "matches"]:
                    if k in raw and isinstance(raw[k], list):
                        raw = raw[k]
                        break
                if isinstance(raw, dict):
                    arr = next((v for v in raw.values() if isinstance(v, list)), None)
                    if arr:
                        raw = arr
            if not isinstance(raw, list):
                return None

            self._set_cached(ck, raw)
            return raw
        except Exception:
            return None

    # ── 4. Priority queue ────────────────────────────────────────────────

    def rank_priority(self, student, evaluations):
        groq_key = os.environ.get("GROQ_API_KEY", "").strip()
        if not groq_key or not evaluations:
            return None

        eval_summaries = {}
        for tid, ev in evaluations.items():
            if not ev:
                continue
            eval_summaries[tid] = {
                "target_name": ev.get("target_name", tid),
                "match_score": ev.get("match_score"),
                "compliant": ev.get("compliant"),
                "risk_level": ev.get("risk_level"),
                "difficulty_label": ev.get("difficulty_label"),
                "gaps": ev.get("gaps", []),
                "remediations": ev.get("remediations", []),
            }

        prompt = f"""You are an expert admissions counselor. Given a student's evaluations across multiple target pathways, rank them by ACTION PRIORITY — what needs the student's attention FIRST.

Student: {student.get("name")} (Class {student.get("class_level")}, Board: {student.get("board")})

Evaluations by target:
{json.dumps(eval_summaries, indent=1)}

Priority factors (in order of importance):
1. Expired or imminent deadlines requiring immediate action
2. Fixable CRITICAL gaps where correction windows are still open
3. Low match scores on high-preference targets
4. Missing prerequisites that can still be addressed
5. Portfolio gaps with time to build

Return ONLY a valid JSON object:
{{"priority_queue": [{{"target_id": "<id>", "priority_score": <0-100>, "priority_reason": "<1 sentence>", "recommended_action": "<specific next step>", "action_deadline": "<YYYY-MM-DD or null>"}}]}}"""

        payload = {
            "model": GROQ_MODEL,
            "messages": [
                {"role": "system", "content": "You are unlockED AI Priority Engine. Return ONLY valid JSON."},
                {"role": "user", "content": prompt},
            ],
            "response_format": {"type": "json_object"},
            "temperature": 0.1,
        }

        res, err = _groq_post_with_retry(groq_key, payload, label="LLMScorer.priority")
        if res is None:
            return None

        try:
            data = json.loads(res.json()["choices"][0]["message"]["content"])
            queue = data.get("priority_queue", data.get("priorities", []))
            if isinstance(queue, list):
                queue.sort(key=lambda x: x.get("priority_score", 0), reverse=True)
                return queue
            return None
        except Exception:
            return None
