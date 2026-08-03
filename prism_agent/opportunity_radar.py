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
        Returns a sorted list of matched opportunities with personalized match explanations.
        """
        matched_list = []
        student_id = student.get("id")
        class_level = int(student.get("class_level", 12))
        
        # Determine student subjects (handle Class 10 vs 11/12)
        if class_level == 10 and student.get("planned_class_11_subjects"):
            subjects = student.get("planned_class_11_subjects", [])
        else:
            subjects = student.get("board_subjects", [])
        norm_subjects = [s.lower().strip() for s in subjects]

        # Check target tracks (elite US/UK paths get bonus recommendations for portfolios)
        targets = student.get("targets", [])
        has_elite_target = any(
            any(kw in t.lower() for kw in ["cambridge", "oxford", "mit", "stanford", "harvard", "imperial", "ucl"])
            for t in targets
        )

        # Use current date in IST (UTC+5:30)
        ist_offset = datetime.timezone(datetime.timedelta(hours=5, minutes=30))
        current_date = datetime.datetime.now(ist_offset).date()

        for comp in competitions:
            min_c = comp.get("min_class_level", 9)
            max_c = comp.get("max_class_level", 12)

            # Class Level constraint check
            if not (min_c <= class_level <= max_c):
                continue

            # Calculate match score
            comp_tags = [t.lower().strip() for t in comp.get("subject_tags", [])]
            matching_subjs = [s for s in subjects if s.lower().strip() in comp_tags]
            
            # Base match score
            if not matching_subjs:
                base_score = 40  # Low match base
            else:
                base_score = 70 + min(20, len(matching_subjs) * 10)  # Multi-subject match bonus

            # Elite target portfolio upgrade bonus
            if has_elite_target and comp.get("portfolio_tier", 3) <= 2:
                base_score += 10
            
            # Grade expectations alignment
            exp_grade_str = student.get("grades", {}).get("current_expected_board", "85%")
            try:
                exp_grade = float(exp_grade_str.replace("%", "").strip())
            except:
                exp_grade = 85.0
            
            if exp_grade >= 92.0 and comp.get("portfolio_tier", 3) == 1:
                base_score += 5

            match_score = min(100, base_score)

            # Generate narrative "Why" explanation
            why_reasons = []
            if matching_subjs:
                why_reasons.append(f"it directly aligns with your board subjects ({', '.join(matching_subjs)})")
            
            if has_elite_target and comp.get("portfolio_tier", 3) <= 2:
                why_reasons.append(f"satisfies the elite extracurricular portfolio requirement (Tier {comp.get('portfolio_tier')}) for your target pathway")
            else:
                why_reasons.append(f"offers a strong extracurricular profile boost (Tier {comp.get('portfolio_tier')})")

            why_expl = "Recommended because " + " and ".join(why_reasons) + "."

            # Calculate days remaining to deadline
            days_left = None
            dl_str = comp.get("deadline", "")
            if dl_str:
                try:
                    dl_date = datetime.datetime.strptime(dl_str, "%Y-%m-%d").date()
                    days_left = (dl_date - current_date).days
                except Exception as e:
                    pass

            matched_list.append({
                "competition": comp,
                "match_score": match_score,
                "matching_subjects": matching_subjs,
                "why": why_expl,
                "days_remaining": days_left,
                "is_urgent": days_left is not None and 0 <= days_left <= 60
            })

        # Sort: match score descending, then deadline urgency
        matched_list.sort(key=lambda x: (x["match_score"], -(x["days_remaining"] if x["days_remaining"] is not None else 9999)), reverse=True)
        return matched_list
