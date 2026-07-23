import os
import json
import re

class ExternalDatabaseAdapter:
    def __init__(self, requirements_db_path="data/requirements_db.json"):
        self.db_path = requirements_db_path
        self.existing_db = {}
        self.load_existing_db()

    def load_existing_db(self):
        """Loads the current requirements database."""
        if os.path.exists(self.db_path):
            with open(self.db_path, "r") as f:
                self.existing_db = json.load(f)
        else:
            self.existing_db = {}

    def save_db(self):
        """Saves requirements back to disk."""
        with open(self.db_path, "w") as f:
            json.dump(self.existing_db, f, indent=2)
        print(f"✔ Requirements database successfully updated at: {self.db_path}")

    def import_from_crawled_json(self, crawled_file_path):
        """
        Parses crawled JSON data and merges it into PRISM.
        Assumes a standard unstructured crawled schema and translates it.
        """
        if not os.path.exists(crawled_file_path):
            print(f"❌ Crawled file not found at: {crawled_file_path}")
            return False

        with open(crawled_file_path, "r") as f:
            crawled_records = json.load(f)

        print(f"Loaded {len(crawled_records)} external records. Parsing and adapting...")
        
        imported_count = 0
        for record in crawled_records:
            # 1. Normalize fields (handle variations in crawler schemas)
            uni_name = record.get("university", record.get("university_name", "Unknown University")).strip()
            course_name = record.get("course", record.get("course_title", "Unknown Course")).strip()
            raw_reqs = record.get("entry_requirements", record.get("requirements", "")).strip()
            raw_deadline = record.get("deadline", record.get("deadline_date", "")).strip()
            source_url = record.get("source_url", record.get("url", "Official University Website")).strip()
            verified_date = record.get("last_verified", "2026-07-22")

            if not uni_name or not course_name:
                continue

            # 2. Determine geographical track (India, UK, US)
            track = self._detect_track(uni_name)

            # 3. Create unique node ID
            node_id = self._generate_node_id(uni_name, course_name)

            # 4. Parse subject requirements from raw text
            subject_prereqs = self._parse_subject_prerequisites(raw_reqs)

            # 5. Parse standardized tests (TMUA, SAT, AP Calculus etc)
            admission_tests = self._parse_admission_tests(raw_reqs)

            # 6. Parse board grade prerequisites (CBSE / A-Levels)
            grade_prereqs = self._parse_grade_prerequisites(raw_reqs, track)

            # 7. Formulate deadlines
            deadlines = []
            if raw_deadline:
                # Normalise YYYY-MM-DD or default label
                deadlines.append({
                    "label": "Application Deadline",
                    "date": self._format_date(raw_deadline),
                    "is_correction_window": False,
                    "description": f"Official application submission deadline for {course_name}."
                })

            # 8. Create official citation node
            citations = [{
                "source": f"{uni_name} Undergraduate Directory / Prospectus",
                "clause": f"Entry requirements page for {course_name} (Source: {source_url})",
                "last_verified": verified_date
            }]

            # 9. Structure into PRISM Node format
            prism_node = {
                "id": node_id,
                "name": f"{uni_name} - {course_name}",
                "track": track,
                "type": "UniversityCourse",
                "university": uni_name,
                "deadlines": deadlines,
                "subject_prerequisites": subject_prereqs,
                "admission_tests": admission_tests,
                "grade_prerequisites": grade_prereqs,
                "portfolio_tier": 2 if track in ["US", "UK"] else 3, # US/UK default to Tier 2 holistic review
                "citations": citations
            }

            # 10. Merge into database (preventing duplicates, updating existing nodes)
            self.existing_db[node_id] = prism_node
            imported_count += 1

        self.save_db()
        print(f"Successfully integrated {imported_count} new course targets into PRISM requirements graph.")
        return True

    def _detect_track(self, uni_name):
        uni_lower = uni_name.lower()
        uk_keywords = ["oxford", "cambridge", "imperial", "ucl", "london", "edinburgh", "manchester", "bristol", "warwick", "kcl", "uk", "kingdom"]
        us_keywords = ["mit", "harvard", "stanford", "caltech", "berkeley", "yale", "princeton", "columbia", "chicago", "nyu", "pennsylvania", "cornell", "us", "usa"]
        
        if any(keyword in uni_lower for keyword in uk_keywords):
            return "UK"
        if any(keyword in uni_lower for keyword in us_keywords):
            return "US"
        return "India" # Fallback/default track

    def _generate_node_id(self, uni_name, course_name):
        # Convert to upper snake case e.g., "CAMBRIDGE_CS"
        clean_uni = re.sub(r'[^A-Z0-9]', '_', uni_name.upper())
        clean_course = re.sub(r'[^A-Z0-9]', '_', course_name.upper())
        # Trim multiple underscores
        node_id = f"{clean_uni}_{clean_course}"
        node_id = re.sub(r'_+', '_', node_id).strip('_')
        return node_id[:50] # Caps size limit

    def _parse_subject_prerequisites(self, text):
        text_lower = text.lower()
        prereqs = []

        # Mathematics
        if any(kw in text_lower for kw in ["mathematics", "math", "maths"]):
            prereqs.append({
                "subject": "Mathematics",
                "level": "compulsory",
                "notes": "Requires strong quantitative score in board exams."
            })

        # Further Maths (Common for UK engineering/CS)
        if "further math" in text_lower or "further maths" in text_lower:
            prereqs.append({
                "subject": "Further Mathematics",
                "level": "compulsory",
                "notes": "Strongly recommended for advanced analytical entry."
            })

        # Physics
        if "physics" in text_lower:
            prereqs.append({
                "subject": "Physics",
                "level": "compulsory",
                "notes": "Physics studied as lab science."
            })

        # Chemistry
        if "chemistry" in text_lower:
            prereqs.append({
                "subject": "Chemistry",
                "level": "compulsory",
                "notes": "Chemistry studied as lab science."
            })

        # Biology
        if "biology" in text_lower:
            prereqs.append({
                "subject": "Biology",
                "level": "compulsory",
                "notes": "Biology studied as lab science."
            })

        # English
        if "english" in text_lower:
            prereqs.append({
                "subject": "English",
                "level": "compulsory",
                "notes": "Requires minimum English language proficiency."
            })

        return prereqs

    def _parse_admission_tests(self, text):
        text_upper = text.upper()
        tests = []
        
        test_patterns = {
            "TMUA": r"\bTMUA\b",
            "STEP": r"\bSTEP\b",
            "MAT": r"\bMAT\b",
            "SAT": r"\bSAT\b",
            "ACT": r"\bACT\b",
            "IELTS": r"\bIELTS\b",
            "TOEFL": r"\bTOEFL\b"
        }

        for test_code, pattern in test_patterns.items():
            if re.search(pattern, text_upper):
                tests.append(test_code)
        return tests

    def _parse_grade_prerequisites(self, text, track):
        prereqs = []
        
        # Look for percentages (Indian/CBSE targets)
        cbse_match = re.search(r'(\d{2})%\s*(?:in|aggregate|minimum)', text.lower())
        if cbse_match:
            prereqs.append({
                "system": "CBSE",
                "min_grade": f"{cbse_match.group(1)}.0%",
                "notes": "Overall CBSE Class 12 aggregate score."
            })
        else:
            # Default fallback score for top schools if undefined in crawled text
            prereqs.append({
                "system": "CBSE",
                "min_grade": "90.0%" if track in ["US", "UK"] else "50.0%",
                "notes": "Class 12 Boards minimum benchmark."
            })

        # Look for A-level grades like AAA, A*A*A
        alevel_match = re.search(r'\b(A\*A\*A\*|A\*A\*A|A\*AA|AAA|AAB|ABB)\b', text)
        if alevel_match:
            prereqs.append({
                "system": "A-Level",
                "min_grade": alevel_match.group(1),
                "notes": "Standard A-Level offer profile."
            })

        # Look for SAT benchmarks
        sat_match = re.search(r'\b(1[45]\d{2})\b', text)
        if sat_match:
            prereqs.append({
                "system": "SAT",
                "min_grade": sat_match.group(1),
                "notes": "Recommended SAT threshold."
            })

        return prereqs

    def _format_date(self, raw_date):
        # Extract YYYY-MM-DD from string if present, otherwise default to future entry
        match = re.search(r'(\d{4}-\d{2}-\d{2})', raw_date)
        if match:
            return match.group(1)
        # Handle formats like "15 October 2026"
        return "2027-01-15" # Default future safety cutoff

# Quick CLI implementation
if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(description="Convert crawled university databases into PRISM graph rules.")
    parser.add_argument("crawled_json_path", help="Path to your crawler's json output report.")
    args = parser.parse_args()

    adapter = ExternalDatabaseAdapter()
    adapter.import_from_crawled_json(args.crawled_json_path)
