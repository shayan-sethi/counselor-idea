import os
import json
import re

try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass

class DocumentIngestionAgent:
    """
    Agentic Data Extraction Engine.
    Uses Gemini LLM (with fallback rules) to parse unstructured student documents
    (transcripts, marks cards, resumes) into normalized student profiles.
    """
    def __init__(self):
        self.api_key = os.environ.get("GEMINI_API_KEY", "").strip()

    def process_documents(self, file_contents_list, file_names_list=None):
        """
        Main extraction entry point.
        file_contents_list: list of strings (or bytes) containing text of uploaded files.
        file_names_list: list of filenames.
        Returns a dict matching the student profile schema.
        """
        combined_text = ""
        if file_names_list:
            for fname, content in zip(file_names_list, file_contents_list):
                content_str = ""
                if fname.lower().endswith(".pdf") and isinstance(content, bytes):
                    try:
                        import io
                        from pypdf import PdfReader
                        reader = PdfReader(io.BytesIO(content))
                        pages_txt = [p.extract_text() for p in reader.pages if p.extract_text()]
                        if pages_txt:
                            content_str = "\n".join(pages_txt)
                    except Exception as pdf_err:
                        print(f"[IngestionAgent] PDF extract error: {pdf_err}")
                
                if not content_str:
                    if isinstance(content, bytes):
                        content_str = content.decode("utf-8", errors="ignore")
                    else:
                        content_str = str(content)

                combined_text += f"\n--- DOCUMENT: {fname} ---\n{content_str}\n"
        else:
            combined_text = "\n".join([str(c) for c in file_contents_list])

        from .board_converter import BoardGradeConverter

        extracted_profile = None
        if self.api_key:
            try:
                extracted_profile = self._extract_with_gemini(combined_text)
            except Exception as e:
                print(f"[IngestionAgent Warning] Gemini extraction failed: {e}. Using fallback rule engine.")

        if not extracted_profile:
            extracted_profile = self._extract_with_rules(combined_text)

        return BoardGradeConverter.standardize_profile_grades(extracted_profile)

    def _extract_with_gemini(self, text):
        from google import genai
        from google.genai import types
        from pydantic import BaseModel, Field
        from typing import List, Dict, Optional

        class PortfolioItem(BaseModel):
            activity: str = Field(description="Activity/Project/Interest Title")
            description: str = Field(description="Full Description including awards/impact")
            tier: int = Field(description="1 for International/National/Patent/Global, 2 for State/Regional/Winner, 3 for School/Local/Hobby")

        class StandardizedTests(BaseModel):
            SAT: Optional[int] = Field(default=None)
            ACT: Optional[int] = Field(default=None)
            AP_CALCULUS_BC: Optional[int] = Field(default=None)

        class SubjectGrade(BaseModel):
            subject_name: str
            grade: float = Field(description="Numeric percentage or letter grade float e.g. 95.0")

        class Grades(BaseModel):
            current_expected_board: str = Field(description="e.g. 92.5%")
            subjects: List[SubjectGrade] = Field(description="Current subjects and their numeric percentage or letter grade float e.g. 95.0")
            g10_subjects: List[SubjectGrade] = Field(description="Grade 10 subjects and their numeric percentage float e.g. 95.0")

        class StudentProfile(BaseModel):
            name: str = Field(description="Student Full Name")
            class_level: int = Field(description="10 or 11 or 12")
            board: str = Field(description="CBSE / ICSE / IB / Cambridge / State Board / A-Levels")
            board_subjects: List[str] = Field(description="Current subjects (e.g. HL/SL subjects for IB)")
            planned_class_11_subjects: List[str] = Field(description="Planned subjects if class_level is 10")
            cuet_subjects: List[str] = Field(description="CUET subjects if applicable")
            grades: Grades
            standardized_tests: StandardizedTests
            portfolio: List[PortfolioItem] = Field(description="List of extracurricular activities, projects, initiatives, hobbies, and sports. DO NOT include academic subjects or grades here.")
            targets: List[str] = Field(description="Target IDs if mentioned, e.g. STANFORD_CS, CUET_DU_CS, MIT_STEM, JEE_MAIN, CAMBRIDGE_CS")

        client = genai.Client(api_key=self.api_key)

        system_prompt = """You are an expert AI admissions officer and transcript parser.
Extract student information from the provided document text and populate the structured schema.

CRITICAL INSTRUCTIONS:
1. STRICT SEPARATION OF ACADEMICS AND EXTRACURRICULARS:
   - "portfolio" array MUST ONLY contain genuine extracurricular activities, sports, hobbies, personal projects (e.g. EpiAlert, apps), internships, or non-academic awards.
   - NEVER add grades, school subjects, standard testing, or board examination results to the "portfolio" array. 
   - E.g., if the resume says "Achieved 9A* in IGCSE ... in English, Physics, Math", DO NOT put these subjects in the portfolio. They belong in "grades.g10_subjects".
2. TIMELINE DISTINCTION (Grade 10 vs Current):
   - Grade 10 / IGCSE / MYP subjects and grades go strictly into "grades.g10_subjects".
   - Grade 11/12 / IBDP / A-Level subjects (e.g. HL Physics, SL English) go strictly into "board_subjects".
   - Do not mix Grade 10 subjects into current board_subjects if the student is in Grade 11/12.
3. CLASS LEVEL: If student is pursuing IB Diploma (IBDP), Grade 11, Grade 12, or A-Levels, set "class_level": 12 and "board": "IB" (or A-Levels/CBSE).
4. IGCSE MARKS: If Grade 10 IGCSE / MYP results are listed (e.g. "Achieved 9A* in IGCSE ... in: English, Physics, Math..."), extract the subjects into "grades.g10_subjects" and assign 95.0 for A* or equivalent.
"""
        response = client.models.generate_content(
            model="gemini-2.0-flash",
            contents=[system_prompt, text],
            config=types.GenerateContentConfig(
                response_mime_type="application/json",
                response_schema=StudentProfile,
            )
        )
        
        data = json.loads(response.text.strip())
        
        # Convert lists back to dictionaries for subjects
        if "grades" in data:
            if "subjects" in data["grades"] and isinstance(data["grades"]["subjects"], list):
                data["grades"]["subjects"] = {item["subject_name"]: item["grade"] for item in data["grades"]["subjects"]}
            if "g10_subjects" in data["grades"] and isinstance(data["grades"]["g10_subjects"], list):
                data["grades"]["g10_subjects"] = {item["subject_name"]: item["grade"] for item in data["grades"]["g10_subjects"]}
                
        return data

    def _extract_with_rules(self, text):
        """Fallback rule-based regex extraction engine."""
        profile = {
            "name": "Extracted Student",
            "class_level": 12,
            "board": "IB",
            "board_subjects": [],
            "planned_class_11_subjects": [],
            "cuet_subjects": [],
            "grades": {
                "current_expected_board": "90.0%",
                "subjects": {},
                "g10_subjects": {}
            },
            "standardized_tests": {},
            "portfolio": [],
            "targets": []
        }

        lines = text.split("\n")

        # Name extraction
        name_match = re.search(r"(?:Name|Student|Candidate):\s*([A-Za-z\s]+)", text, re.IGNORECASE)
        if name_match:
            clean_name = name_match.group(1).strip().split("\n")[0]
            if len(clean_name) < 40:
                profile["name"] = clean_name
        else:
            for l in lines[:5]:
                clean_l = l.strip()
                if len(clean_l) > 3 and len(clean_l) < 35 and not any(kw in clean_l.lower() for kw in ["resume", "curriculum", "email", "phone", "profile", "page"]):
                    profile["name"] = clean_l
                    break

        # Board & Class level detection
        has_ib = bool(re.search(r"\bIB\b|\bIBDP\b|\bBaccalaureate\b|\bDiploma Programme\b", text, re.IGNORECASE))
        has_alevel = bool(re.search(r"\bA-Level\b|\bA Levels\b", text, re.IGNORECASE))
        has_g12 = bool(re.search(r"Grade 12|Class 12|12th|Grade 11|Class 11|Senior", text, re.IGNORECASE))
        has_sat = bool(re.search(r"SAT[^\d\n]*?(\d{4})", text, re.IGNORECASE))

        if has_ib or has_alevel or has_g12 or has_sat:
            profile["class_level"] = 12
            profile["board"] = "IB" if has_ib else ("A-Levels" if has_alevel else "CBSE")
        elif re.search(r"Class 10|Grade 10|10th", text, re.IGNORECASE) and not has_ib:
            profile["class_level"] = 10
            profile["board"] = "Cambridge" if "IGCSE" in text else "CBSE"

        known_subjects = [
            "Mathematics", "Physics", "Chemistry", "Biology", "Computer Science",
            "Economics", "English", "Spanish", "Geography", "Environmental Management",
            "Literature", "History", "Accountancy", "Business Studies", "Further Mathematics"
        ]
        detected_subjects = []

        from .board_converter import BoardGradeConverter

        # 1. Check for header-inherited IGCSE Grade
        parent_igcse_match = re.search(r"(?:Achieved|Obtained|Scored|Got|\b)(\d+)?\s*(A\*|A|B|7|8|9|Astar)\s+in[^\n]*?:\s*\n((?:[^\n]+\n){1,15})", text, re.IGNORECASE)
        if parent_igcse_match:
            inherited_grade = parent_igcse_match.group(2)
            sub_block = parent_igcse_match.group(3)
            pct_val, _ = BoardGradeConverter.convert_grade(inherited_grade, class_level=10, board="IGCSE")
            target_pct = pct_val or 95.0
            for sub in known_subjects:
                if re.search(rf"\b{sub}\b", sub_block, re.IGNORECASE):
                    profile["grades"]["g10_subjects"][sub] = target_pct

        # 2. Standard per-subject lookup
        for sub in known_subjects:
            if re.search(rf"\b{sub}\b", text, re.IGNORECASE):
                if sub not in detected_subjects:
                    detected_subjects.append(sub)

                igcse_m = re.search(rf"\b{sub}\b[^\n]*?\b(A\*|A|B|C|D|E|F|9|8|7|6|5)\b", text, re.IGNORECASE)
                if igcse_m and sub not in profile["grades"]["g10_subjects"]:
                    raw_g10 = igcse_m.group(1)
                    pct_g10, _ = BoardGradeConverter.convert_grade(raw_g10, class_level=10, board="IGCSE")
                    if pct_g10:
                        profile["grades"]["g10_subjects"][sub] = pct_g10

                grade_m = re.search(rf"\b{sub}\b[^\d\n]*?(\d{{2,3}}(?:\.\d+)?)", text, re.IGNORECASE)
                if grade_m:
                    try:
                        val = float(grade_m.group(1))
                        if 0 <= val <= 100:
                            profile["grades"]["subjects"][sub] = val
                    except ValueError:
                        pass

        if profile["class_level"] == 10:
            profile["planned_class_11_subjects"] = detected_subjects if detected_subjects else ["Economics", "Commerce", "English"]
        else:
            profile["board_subjects"] = detected_subjects if detected_subjects else ["Physics", "Chemistry", "Mathematics", "English"]

        # SAT score check
        sat_m = re.search(r"SAT[^\d\n]*?(\d{4})", text, re.IGNORECASE)
        if sat_m:
            profile["standardized_tests"]["SAT"] = int(sat_m.group(1))

        # 3. Extracurriculars, Initiatives, Projects, Hobbies & Interests Section Parsing
        ec_keywords = [
            "initiatives", "initiative", "projects", "project", "epialert", "pollution alert",
            "interests", "interest", "extracurricular", "extracurriculars", "achievements",
            "activities", "leadership", "sports", "swimmer", "swimming", "award", "awards",
            "patent", "competition", "gold", "olympiad", "space settlement", "ukmt", "scuba",
            "python", "ml", "tech", "device", "prototype", "google", "times of india"
        ]

        in_ec_section = False
        current_item = []

        for line in lines:
            line_str = line.strip()
            if not line_str:
                if current_item and in_ec_section:
                    full_desc = " ".join(current_item).strip()
                    if len(full_desc) > 10:
                        tier = 3
                        if any(kw in full_desc.lower() for kw in ["patent", "national", "international", "apj abdul kalam", "google", "times of india", "world school games", "gold", "asian regional", "olympiad", "first place"]):
                            tier = 1
                        elif any(kw in full_desc.lower() for kw in ["award", "winner", "president", "founder", "plaksha", "competiton", "regional"]):
                            tier = 2
                        
                        clean_bullet = re.sub(r"^[•o▪\-\*\s]+", "", full_desc).strip()
                        title = clean_bullet.split(":")[0] if ":" in clean_bullet else clean_bullet[:40]
                        if not any(item["description"] == clean_bullet for item in profile["portfolio"]):
                            profile["portfolio"].append({
                                "activity": title[:45],
                                "description": clean_bullet,
                                "tier": tier
                            })
                    current_item = []
                continue

            is_academic_header = len(line_str) < 40 and any(sec in line_str.lower() for sec in ["education", "academic", "subject", "subjects", "standardised test", "standardised testing", "standardized testing"])
            if is_academic_header:
                in_ec_section = False
                continue

            # Header detection
            is_header = len(line_str) < 40 and any(sec in line_str.lower() for sec in ["initiative", "initiatives", "projects", "hobbies", "interests", "extracurriculars", "achievements", "activities", "leadership", "honors", "sports"]) and not line_str.startswith("•") and not line_str.startswith("o") and not line_str.startswith("▪")
            if is_header:
                in_ec_section = True
                continue

            clean_bullet = re.sub(r"^[•o▪\-\*\s]+", "", line_str).strip()
            if clean_bullet.startswith("http://") or clean_bullet.startswith("https://") or clean_bullet.lower().startswith("media coverage"):
                if current_item:
                    current_item.append(clean_bullet)
                continue

            if in_ec_section:
                # If bullet point or new paragraph header
                if line_str.startswith("•") or line_str.startswith("o") or line_str.startswith("▪") or (":" in clean_bullet and len(clean_bullet.split(":")[0]) < 25):
                    if current_item:
                        full_desc = " ".join(current_item).strip()
                        if len(full_desc) > 10:
                            tier = 3
                            if any(kw in full_desc.lower() for kw in ["patent", "national", "international", "apj abdul kalam", "google", "times of india", "world school games", "gold", "asian regional", "olympiad", "first place"]):
                                tier = 1
                            elif any(kw in full_desc.lower() for kw in ["award", "winner", "president", "founder", "plaksha", "competiton", "regional"]):
                                tier = 2
                            title = full_desc.split(":")[0] if ":" in full_desc else full_desc[:40]
                            if not any(item["description"] == full_desc for item in profile["portfolio"]):
                                profile["portfolio"].append({
                                    "activity": title[:45],
                                    "description": full_desc,
                                    "tier": tier
                                })
                    current_item = [clean_bullet]
                else:
                    current_item.append(clean_bullet)

        if current_item:
            full_desc = " ".join(current_item).strip()
            if len(full_desc) > 10:
                tier = 3
                if any(kw in full_desc.lower() for kw in ["patent", "national", "international", "apj abdul kalam", "google", "times of india", "world school games", "gold", "asian regional", "olympiad", "first place"]):
                    tier = 1
                elif any(kw in full_desc.lower() for kw in ["award", "winner", "president", "founder", "plaksha", "competiton", "regional"]):
                    tier = 2
                title = full_desc.split(":")[0] if ":" in full_desc else full_desc[:40]
                if not any(item["description"] == full_desc for item in profile["portfolio"]):
                    profile["portfolio"].append({
                        "activity": title[:45],
                        "description": full_desc,
                        "tier": tier
                    })

        return profile
