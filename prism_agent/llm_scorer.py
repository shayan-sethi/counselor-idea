import os
import json
import time

GROQ_MODEL = "llama-3.3-70b-versatile"

ELITE_KEYWORDS = [
    "cambridge", "oxford", "mit", "stanford", "harvard", "yale", "princeton",
    "caltech", "imperial", "iit bombay", "iit delhi", "iit madras", "aiims",
    "columbia", "chicago", "iisc", "lse", "london school of economics",
]

HARD_BLOCK_TYPES = {"subject_missing", "cuet_missing_subject", "cuet_unlawful_domain"}

from .groq_utils import get_groq_api_keys, groq_post_with_retry


def _call_groq(payload, label="Groq"):
    return groq_post_with_retry(payload, label=label, max_wait=12)


class LLMScorer:

    def __init__(self):
        self._cache = {}
        self._cache_ttl = 300

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
        if not get_groq_api_keys() or not student or not target:
            return None

        ck = self._cache_key("score", student.get("id"), target.get("id", target.get("name")))
        cached = self._get_cached(ck)
        if cached:
            return cached

        grade = student.get("grades", {}).get("current_expected_board", "N/A")
        tests = student.get("standardized_tests", {})
        best_tier = min([a.get("tier", 3) for a in student.get("portfolio", [])] or [4])
        admission_tests = target.get("admission_tests", [])

        gap_summary = [g.get("issue", g.get("field", "gap")) for g in gaps[:5]] if gaps else []

        prompt = f"""Score student vs target. Return JSON only.

Student: grade={grade}, board={student.get("board")}, subjects={student.get("board_subjects", [])}, SAT={tests.get("SAT","N/A")}, portfolio_tier={best_tier}
Target: {target.get("name")}, track={target.get("track")}, uni={target.get("university")}, tests={admission_tests}, portfolio_tier={target.get("portfolio_tier")}
Gaps: {gap_summary}

Rules: CUET/JEE targets NEVER "Safety". Elite unis cap 78. Max 92. CRITICAL subject_missing => <=35.

{{"match_score":<int>,"risk_level":"<label>","difficulty_label":"<Safety|Target|Reach>","scoring_rationale":"<1 sentence>"}}"""

        payload = {
            "model": GROQ_MODEL,
            "messages": [
                {"role": "system", "content": "Return ONLY valid JSON."},
                {"role": "user", "content": prompt},
            ],
            "response_format": {"type": "json_object"},
            "temperature": 0.1,
            "max_tokens": 200,
        }

        res, err = _call_groq(payload, label="LLMScorer.score")
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

    def classify_shortlist(self, student, college, requirements_info=None):
        if not get_groq_api_keys():
            return None

        college_name = college.get("name", "Unknown")
        ck = self._cache_key("shortlist", student.get("id"), college.get("id", college_name))
        cached = self._get_cached(ck)
        if cached:
            return cached

        grade = student.get("grades", {}).get("current_expected_board") or student.get("grades", {}).get("class_12_aggregate") or "80"
        tests = student.get("standardized_tests", {})
        sat = tests.get("SAT") or tests.get("sat") or 0
        best_tier = min([a.get("tier", 3) for a in student.get("portfolio", [])] or [4])
        required_exams = college.get("admission_tests", college.get("required_exams", []))
        country = college.get("country", college.get("track", ""))

        req_line = ""
        if requirements_info:
            subj_reqs = [p.get("subject") for p in requirements_info.get("subject_prerequisites", []) if p.get("level") == "compulsory"]
            grade_reqs = [f"{g.get('system')}:{g.get('min_grade')}" for g in requirements_info.get("grade_prerequisites", [])]
            req_line = f"Required subjects: {subj_reqs}. Grade reqs: {grade_reqs}. Admission tests: {requirements_info.get('admission_tests', [])}."

        prompt = f"""Evaluate admission chances. Return JSON only.

Student: grade={grade}, SAT={sat}, board={student.get("board","?")}, subjects={student.get("board_subjects",[])}, portfolio_tier={best_tier}
College: {college_name}, country={country}, exams={required_exams}
{req_line}

Rules:
- IMPORTANT: CUET and JEE are Indian entrance exams. NEVER mention, require, or list CUET/JEE as missing for US, UK, or International universities!
- CUET/JEE rules apply ONLY if target is an Indian university.
- Elite unis cap match_score at 78. Range 5-92.

{{"category":"<Safety|Target|Reach>","match_score":<int>,"tier":<1-4>,"reasoning":"<1-2 sentences>","gaps":["<gap>"],"strengths":["<strength>"]}}"""

        payload = {
            "model": GROQ_MODEL,
            "messages": [
                {"role": "system", "content": "Return ONLY valid JSON."},
                {"role": "user", "content": prompt},
            ],
            "response_format": {"type": "json_object"},
            "temperature": 0.1,
            "max_tokens": 250,
        }

        res, err = _call_groq(payload, label="LLMScorer.shortlist")
        if res is None:
            return None

        try:
            data = json.loads(res.json()["choices"][0]["message"]["content"])
            category = data.get("category", "Target")
            tier = int(data.get("tier", 3))
            match_score = int(data.get("match_score", 50))

            if any(t in ("CUET_UG", "JEE_MAIN", "JEE_ADVANCED", "JEE Mains") for t in required_exams):
                if category == "Safety":
                    category = "Target"

            name_lower = college_name.lower()
            if any(kw in name_lower for kw in ELITE_KEYWORDS):
                match_score = min(match_score, 78)
                if category == "Safety":
                    category = "Target"

            match_score = max(5, min(92, match_score))

            gaps = data.get("gaps", [])
            if not isinstance(gaps, list):
                gaps = []

            # Sanitize gaps: filter out any CUET or JEE mentions for non-Indian universities
            country_str = str(country).upper() if country else ""
            if country_str not in ("IN", "IND", "INDIA"):
                gaps = [g for g in gaps if not any(x in str(g).upper() for x in ("CUET", "JEE"))]

            result = {
                "category": category,
                "tier": tier,
                "match_score": match_score,
                "reasoning": data.get("reasoning", ""),
                "gaps": gaps,
                "strengths": data.get("strengths", []),
            }
            self._set_cached(ck, result)
            return result
        except Exception:
            return None

    # ── 3. Score opportunities (batch) ───────────────────────────────────

    def score_opportunities(self, student, competitions):
        if not get_groq_api_keys() or not competitions:
            return None

        ck = self._cache_key("opps", student.get("id"), len(competitions))
        cached = self._get_cached(ck)
        if cached:
            return cached

        comps_brief = [{"id": c.get("id"), "name": c.get("name"), "tags": c.get("subject_tags", [])[:3], "tier": c.get("portfolio_tier", 3)} for c in competitions[:10]]

        prompt = f"""Score competition fit for student (0-100). Return JSON array.

Student subjects: {student.get("board_subjects", [])}, targets: {student.get("targets", [])[:3]}, grade: {student.get("grades",{}).get("current_expected_board","N/A")}

Competitions: {json.dumps(comps_brief)}

[{{"competition_id":"<id>","match_score":<0-100>,"why":"<1 sentence>","is_urgent":false}}]"""

        payload = {
            "model": GROQ_MODEL,
            "messages": [
                {"role": "system", "content": "Return ONLY valid JSON."},
                {"role": "user", "content": prompt},
            ],
            "response_format": {"type": "json_object"},
            "temperature": 0.15,
            "max_tokens": 400,
        }

        res, err = _call_groq(payload, label="LLMScorer.opps")
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
        if not get_groq_api_keys() or not evaluations:
            return None

        brief = {}
        for tid, ev in evaluations.items():
            if not ev:
                continue
            brief[tid] = {
                "name": ev.get("target_name", tid),
                "score": ev.get("match_score"),
                "risk": ev.get("risk_level"),
                "gaps": len(ev.get("gaps", [])),
            }

        prompt = f"""Rank targets by action priority. Return JSON.

Student: {student.get("name")} (Class {student.get("class_level")})
Targets: {json.dumps(brief)}

{{"priority_queue":[{{"target_id":"<id>","priority_score":<0-100>,"priority_reason":"<1 sentence>","recommended_action":"<next step>"}}]}}"""

        payload = {
            "model": GROQ_MODEL,
            "messages": [
                {"role": "system", "content": "Return ONLY valid JSON."},
                {"role": "user", "content": prompt},
            ],
            "response_format": {"type": "json_object"},
            "temperature": 0.1,
            "max_tokens": 400,
        }

        res, err = _call_groq(payload, label="LLMScorer.priority")
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
