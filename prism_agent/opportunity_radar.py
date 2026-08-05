import os
import re
import json
import urllib.request
import datetime

class CompeteMapScraper:
    @staticmethod
    def scrape_url(url):
        """
        Scrapes a competition page from CompeteMap.
        Extracts metadata and structures it into a competition object.
        """
        try:
            req = urllib.request.Request(
                url, 
                headers={'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64)'}
            )
            with urllib.request.urlopen(req, timeout=10) as response:
                html = response.read().decode('utf-8')
        except Exception as e:
            print(f"Error fetching URL: {e}")
            return None

        # 1. Title/Name extraction
        title_m = re.search(r"<title>(.*?)</title>", html)
        title = title_m.group(1) if title_m else "Unknown Competition"
        if " | CompeteMap" in title:
            name = title.replace(" | CompeteMap", "").strip()
        else:
            name = title.strip()

        # 2. Meta description extraction
        desc_m = re.search(r'<meta name="description" content="(.*?)"', html)
        desc_content = desc_m.group(1) if desc_m else ""

        # 3. Parse details from meta description
        # Example: "Breakthrough Junior Challenge is a science competition listed under International / Other for ages 13-18. Secondary school students aged 13-18 worldwide. Registration deadline 15 Sept 2026. Fee: Free."
        description = desc_content
        comp_type = "Competition"
        min_class = 9
        max_class = 12
        deadline = "2026-09-15"
        fee = "Free"

        if desc_content:
            # Detect competition type
            type_match = re.search(r"is a (.*?) listed under", desc_content, re.IGNORECASE)
            if type_match:
                comp_type = type_match.group(1).strip().capitalize()

            # Detect age group -> convert to class levels
            age_match = re.search(r"for ages (\d+)-(\d+)", desc_content, re.IGNORECASE)
            if age_match:
                min_age = int(age_match.group(1))
                max_age = int(age_match.group(2))
                
                # Simple age-to-class-level mapping
                if min_age >= 16:
                    min_class = 11
                elif min_age >= 15:
                    min_class = 10
                else:
                    min_class = 9

                if max_age <= 15:
                    max_class = 10
                elif max_age <= 16:
                    max_class = 11
                else:
                    max_class = 12

            # Detect fee
            fee_match = re.search(r"Fee:\s*(.*?)(?:\.|$)", desc_content, re.IGNORECASE)
            if fee_match:
                fee = fee_match.group(1).strip()

            # Detect deadline
            deadline_match = re.search(r"Registration deadline\s*(.*?)(?:\.|$)", desc_content, re.IGNORECASE)
            if deadline_match:
                raw_dl = deadline_match.group(1).strip()
                parsed_dl = CompeteMapScraper._parse_date_string(raw_dl)
                if parsed_dl:
                    deadline = parsed_dl

        # 4. Generate subject tags based on text analysis
        text_to_search = (name + " " + description).lower()
        tags = []
        
        # Science/STEM mapping
        science_keywords = ["science", "physics", "chemistry", "biology", "stem", "life science", "space", "nature"]
        if any(kw in text_to_search for kw in science_keywords):
            tags.extend(["Physics", "Chemistry", "Biology", "Science", "Computer Science"])

        # Math mapping
        math_keywords = ["math", "mathematics", "calculus", "algebra", "geometry", "tournament", "olympiad"]
        if any(kw in text_to_search for kw in math_keywords):
            tags.extend(["Mathematics", "Further Mathematics"])

        # Humanities / Writing mapping
        humanities_keywords = ["essay", "writing", "english", "literature", "history", "philosophy", "politics", "law", "humanities"]
        if any(kw in text_to_search for kw in humanities_keywords):
            tags.extend(["English Core", "Elective English", "History", "Political Science", "Economics"])

        # Economics / Commerce mapping
        commerce_keywords = ["economics", "commerce", "finance", "business", "investment", "accounting"]
        if any(kw in text_to_search for kw in commerce_keywords):
            tags.extend(["Economics", "Business Studies", "Accountancy"])

        # Default tags if none match
        if not tags:
            tags = ["Science", "Mathematics", "Economics", "History"]
        else:
            tags = list(set(tags))  # Deduplicate

        # Extract ID from URL
        comp_id = url.split("/")[-1].split("?")[0]
        if not comp_id:
            comp_id = f"custom_comp_{int(datetime.datetime.now().timestamp())}"

        return {
            "id": comp_id,
            "name": name,
            "type": comp_type,
            "subject_tags": tags,
            "min_class_level": min_class,
            "max_class_level": max_class,
            "deadline": deadline,
            "portfolio_tier": 1 if "olympiad" in text_to_search or "challenge" in text_to_search or "john locke" in text_to_search or "breakthrough" in text_to_search else 2,
            "description": description or f"A prestigious competition imported from CompeteMap. Fits tracks: {', '.join(tags)}.",
            "fee": fee,
            "url": url
        }

    @staticmethod
    def _parse_date_string(date_str):
        """Parses raw strings like '15 Sept 2026' or 'September 30, 2026' to YYYY-MM-DD."""
        months = {
            "jan": "01", "feb": "02", "mar": "03", "apr": "04", "may": "05", "jun": "06",
            "jul": "07", "aug": "08", "sep": "09", "oct": "10", "nov": "11", "dec": "12",
            "january": "01", "february": "02", "march": "03", "april": "04", "june": "06",
            "july": "07", "august": "08", "september": "09", "october": "10", "november": "11", "december": "12"
        }
        try:
            # Clean string
            date_str = date_str.replace(",", "").replace(".", "").strip().lower()
            
            # Match formats like: "15 sept 2026"
            m1 = re.search(r"(\d{1,2})\s+([a-z]+)\s+(\d{4})", date_str)
            if m1:
                day = int(m1.group(1))
                mon_str = m1.group(2)
                year = m1.group(3)
                mon = months.get(mon_str, "09")
                return f"{year}-{mon}-{day:02d}"

            # Match formats like: "september 30 2026"
            m2 = re.search(r"([a-z]+)\s+(\d{1,2})\s+(\d{4})", date_str)
            if m2:
                mon_str = m2.group(1)
                day = int(m2.group(2))
                year = m2.group(3)
                mon = months.get(mon_str, "09")
                return f"{year}-{mon}-{day:02d}"
        except Exception as e:
            print(f"Error parsing date string: {e}")
        return None


class OpportunityRadar:
    @staticmethod
    def match_student(student, competitions):
        """
        Evaluates a student against all competitions.
        Uses LLM scoring when available, falls back to deterministic formula.
        """
        class_level = int(student.get("class_level", 12))
        ist_offset = datetime.timezone(datetime.timedelta(hours=5, minutes=30))
        current_date = datetime.datetime.now(ist_offset).date()

        if class_level == 10 and student.get("planned_class_11_subjects"):
            subjects = student.get("planned_class_11_subjects", [])
        else:
            subjects = student.get("board_subjects", [])

        eligible = []
        for c in competitions:
            if not (c.get("min_class_level", 9) <= class_level <= c.get("max_class_level", 12)):
                continue
            dl_str = c.get("deadline", "")
            if dl_str:
                try:
                    dl_date = datetime.datetime.strptime(dl_str, "%Y-%m-%d").date()
                    if dl_date < current_date:
                        continue
                except Exception:
                    pass
            eligible.append(c)

        if not eligible:
            return []

        return OpportunityRadar._match_deterministic(student, eligible, subjects, current_date)

    @staticmethod
    def _match_deterministic(student, eligible, subjects, current_date):
        matched_list = []
        targets = student.get("targets", [])
        targets_lower = [t.lower() for t in targets]
        grades_dict = student.get("grades", {}).get("subjects", {})
        portfolio = student.get("portfolio", [])
        tests = student.get("standardized_tests", {})

        elite_keywords = ["cambridge", "oxford", "mit", "stanford", "harvard", "imperial", "ucl", "princeton", "yale", "columbia", "caltech", "lse"]
        has_elite_target = any(any(kw in t for kw in elite_keywords) for t in targets_lower)

        target_fields = OpportunityRadar._infer_target_fields(targets_lower)
        portfolio_keywords = OpportunityRadar._extract_portfolio_keywords(portfolio)

        for comp in eligible:
            comp_tags = [t.lower().strip() for t in comp.get("subject_tags", [])]
            matching_subjs = [s for s in subjects if s.lower().strip() in comp_tags]
            comp_name_lower = comp.get("name", "").lower()
            comp_desc_lower = comp.get("description", "").lower()
            comp_type_lower = comp.get("type", "").lower()
            comp_tier = comp.get("portfolio_tier", 3)

            score = 0
            why_parts = []

            # --- 1. Subject overlap (0-30) ---
            if matching_subjs:
                overlap_ratio = len(matching_subjs) / max(len(subjects), 1)
                subject_pts = min(30, int(overlap_ratio * 30) + len(matching_subjs) * 5)
                score += subject_pts
                why_parts.append(f"Matches {len(matching_subjs)} of {len(subjects)} subjects ({', '.join(matching_subjs)})")
            else:
                score += 5

            # --- 2. Grade strength in matching subjects (0-20) ---
            if matching_subjs and grades_dict:
                matched_grades = [grades_dict[s] for s in matching_subjs if s in grades_dict]
                if matched_grades:
                    avg_grade = sum(matched_grades) / len(matched_grades)
                    if avg_grade >= 95:
                        score += 20
                        why_parts.append(f"Avg {avg_grade:.0f}% in matched subjects — exceptional fit")
                    elif avg_grade >= 90:
                        score += 15
                        why_parts.append(f"Strong grades ({avg_grade:.0f}%) in relevant subjects")
                    elif avg_grade >= 85:
                        score += 10
                    elif avg_grade >= 80:
                        score += 5

            # --- 3. Target university alignment (0-20) ---
            target_pts = 0
            target_reason = None
            for t in targets_lower:
                if any(kw in comp_name_lower or kw in comp_desc_lower for kw in t.split() if len(kw) > 3):
                    target_pts = max(target_pts, 15)
                    target_reason = f"Directly linked to target: {t.title()}"

            comp_field = OpportunityRadar._classify_comp_field(comp_tags, comp_type_lower, comp_name_lower)
            if comp_field and comp_field in target_fields:
                target_pts = max(target_pts, 10)
                if not target_reason:
                    target_reason = f"Aligns with {comp_field} focus from target list"

            if has_elite_target and comp_tier == 1:
                target_pts = max(target_pts, 12)
                if not target_reason:
                    target_reason = f"Tier-1 competition strengthens elite university applications"

            score += min(20, target_pts)
            if target_reason:
                why_parts.append(target_reason)

            # --- 4. Portfolio relevance (0-15) ---
            portfolio_pts = 0
            if portfolio_keywords:
                relevance_hits = 0
                for kw in portfolio_keywords:
                    if kw in comp_name_lower or kw in comp_desc_lower or kw in comp_type_lower:
                        relevance_hits += 1
                if relevance_hits >= 3:
                    portfolio_pts = 15
                    why_parts.append("Strong synergy with existing extracurriculars")
                elif relevance_hits >= 1:
                    portfolio_pts = 8
                    why_parts.append("Builds on existing portfolio activities")

            if len(portfolio) <= 1:
                portfolio_pts = max(portfolio_pts, 10)
                if not any("portfolio" in w.lower() for w in why_parts):
                    why_parts.append("Student needs more extracurriculars — high portfolio-building value")
            score += min(15, portfolio_pts)

            # --- 5. Academic profile strength (0-10) ---
            profile_pts = 0
            sat = tests.get("SAT", 0)
            act = tests.get("ACT", 0)
            if sat >= 1450 or act >= 32:
                profile_pts += 5
            elif sat >= 1350 or act >= 29:
                profile_pts += 3

            exp_grade_str = student.get("grades", {}).get("current_expected_board", "85%")
            try:
                exp_grade = float(exp_grade_str.replace("%", "").strip())
            except:
                exp_grade = 85.0
            if exp_grade >= 93:
                profile_pts += 5
            elif exp_grade >= 88:
                profile_pts += 3
            score += min(10, profile_pts)

            # --- 6. Competition prestige fit (0-5) ---
            if comp_tier == 1 and has_elite_target:
                score += 5
            elif comp_tier == 2:
                score += 3
            elif comp_tier == 1:
                score += 2

            match_score = min(100, max(10, score))

            if not why_parts:
                why_parts.append(f"Broadens portfolio as a Tier-{comp_tier} opportunity")

            why_expl = ". ".join(why_parts) + "."

            days_left = None
            dl_str = comp.get("deadline", "")
            if dl_str:
                try:
                    dl_date = datetime.datetime.strptime(dl_str, "%Y-%m-%d").date()
                    days_left = (dl_date - current_date).days
                except Exception:
                    pass

            matched_list.append({
                "competition": comp,
                "match_score": match_score,
                "matching_subjects": matching_subjs,
                "why": why_expl,
                "days_remaining": days_left,
                "is_urgent": days_left is not None and 0 <= days_left <= 60,
            })

        matched_list.sort(key=lambda x: (x["match_score"], -(x["days_remaining"] if x["days_remaining"] is not None else 9999)), reverse=True)
        return matched_list

    @staticmethod
    def _infer_target_fields(targets_lower):
        fields = set()
        stem_kw = ["cs", "computer", "engineering", "tech", "data", "ai", "stem", "iit"]
        science_kw = ["medicine", "medical", "aiims", "bio", "premed", "science"]
        humanities_kw = ["law", "arts", "literature", "english", "philosophy", "history", "politics"]
        econ_kw = ["economics", "econ", "finance", "business", "commerce", "srcc", "lse", "management"]

        for t in targets_lower:
            if any(kw in t for kw in stem_kw):
                fields.add("stem")
            if any(kw in t for kw in science_kw):
                fields.add("science")
            if any(kw in t for kw in humanities_kw):
                fields.add("humanities")
            if any(kw in t for kw in econ_kw):
                fields.add("economics")
        return fields

    @staticmethod
    def _classify_comp_field(comp_tags, comp_type, comp_name):
        text = " ".join(comp_tags) + " " + comp_type + " " + comp_name
        if any(kw in text for kw in ["computer", "coding", "programming", "algorithm", "hackathon"]):
            return "stem"
        if any(kw in text for kw in ["physics", "chemistry", "biology", "science"]):
            return "science"
        if any(kw in text for kw in ["essay", "writing", "literature", "history", "philosophy", "politics", "law"]):
            return "humanities"
        if any(kw in text for kw in ["economics", "business", "finance", "accountancy", "commerce"]):
            return "economics"
        if any(kw in text for kw in ["math", "mathematics"]):
            return "stem"
        return None

    @staticmethod
    def _extract_portfolio_keywords(portfolio):
        keywords = set()
        kw_map = {
            "science": ["science", "research", "lab", "experiment", "biology", "physics", "chemistry"],
            "math": ["math", "olympiad", "quiz", "competition"],
            "writing": ["essay", "writing", "blog", "journalism", "editor", "literary", "debate"],
            "tech": ["code", "coding", "app", "software", "tech", "robot", "hack", "program", "web", "ai", "ml"],
            "leadership": ["president", "founder", "lead", "captain", "head"],
            "mun": ["mun", "model united nations", "delegate"],
            "social": ["ngo", "volunteer", "community", "teach", "social"],
            "sport": ["swim", "sport", "athlete", "cricket", "football", "tennis", "chess"],
            "art": ["art", "music", "dance", "theatre", "drama", "sing", "choir", "photograph"],
        }
        for item in portfolio:
            text = (item.get("activity", "") + " " + item.get("description", "")).lower()
            for category, kws in kw_map.items():
                if any(kw in text for kw in kws):
                    keywords.add(category)
        return keywords
