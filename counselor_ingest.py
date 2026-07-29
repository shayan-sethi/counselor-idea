#!/usr/bin/env python3
"""
Counselor Data Ingestion Script — unlockED Counselor Co-Pilot
============================================================
Allows counselors to batch upload and ingest student data (resumes, transcripts, marks cards, profile documents)
directly into unlockED's student database and knowledge graph.

Usage:
  python counselor_ingest.py --file student_resume.pdf
  python counselor_ingest.py --file transcript.pdf --name "Aarav Sharma"
  python counselor_ingest.py --dir ./counselor_uploads/
  python counselor_ingest.py --interactive
"""

import sys
import os
import json
import argparse
from pathlib import Path

# Ensure root directory is in sys.path
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
if BASE_DIR not in sys.path:
    sys.path.insert(0, BASE_DIR)

from prism_agent.ingestion_agent import DocumentIngestionAgent

STUDENTS_DB_PATH = os.path.join(BASE_DIR, "data", "students_db.json")

def load_students_db():
    if os.path.exists(STUDENTS_DB_PATH):
        with open(STUDENTS_DB_PATH, "r", encoding="utf-8") as f:
            return json.load(f)
    return []

def save_students_db(students):
    os.makedirs(os.path.dirname(STUDENTS_DB_PATH), exist_ok=True)
    with open(STUDENTS_DB_PATH, "w", encoding="utf-8") as f:
        json.dump(students, f, indent=2, ensure_ascii=False)

def generate_next_student_id(students):
    nums = []
    for s in students:
        sid = s.get("id", "")
        if sid.startswith("STU_"):
            try:
                nums.append(int(sid.replace("STU_", "")))
            except ValueError:
                pass
    next_num = max(nums) + 1 if nums else 1
    return f"STU_{next_num:03d}"

def extract_file_content(file_path):
    path = Path(file_path)
    if not path.exists():
        raise FileNotFoundError(f"File not found: {file_path}")
    
    ext = path.suffix.lower()
    if ext == ".pdf":
        try:
            import io
            from pypdf import PdfReader
            with open(path, "rb") as f:
                reader = PdfReader(f)
                text = "\n".join([page.extract_text() for page in reader.pages if page.extract_text()])
                if text.strip():
                    return text
        except Exception as e:
            print(f"[Counselor Ingest Warning] PDF reading issue with pypdf ({e}), falling back to text read.")
    
    with open(path, "r", encoding="utf-8", errors="ignore") as f:
        return f.read()

def ingest_student_documents(file_paths, override_name=None):
    """
    Core function for counselors to ingest one or multiple document files for a student.
    Returns the parsed student dictionary.
    """
    print(f"\n==================================================")
    print(f"🎓 COUNSELOR DATA INGESTION ENGINE")
    print(f"==================================================")
    
    contents = []
    filenames = []
    for fp in file_paths:
        print(f"[+] Reading counselor input document: {fp}")
        c = extract_file_content(fp)
        contents.append(c)
        filenames.append(os.path.basename(fp))
        
    ingestion_agent = DocumentIngestionAgent()
    print("[*] Parsing profile details via DocumentIngestionAgent (AI / Rule fallback)...")
    profile = ingestion_agent.process_documents(contents, filenames)
    
    if override_name:
        profile["name"] = override_name
        
    students = load_students_db()
    
    # Check if student with matching name exists to update, else create new
    existing_idx = None
    for idx, s in enumerate(students):
        if s.get("name", "").strip().lower() == profile.get("name", "").strip().lower():
            existing_idx = idx
            break
            
    if existing_idx is not None:
        student_id = students[existing_idx]["id"]
        print(f"[✓] Existing student profile found: {student_id} ({profile['name']}). Updating profile...")
        profile["id"] = student_id
        students[existing_idx] = profile
    else:
        student_id = generate_next_student_id(students)
        profile["id"] = student_id
        print(f"[✓] Created new student record: {student_id} ({profile['name']}).")
        students.append(profile)
        
    save_students_db(students)
    print(f"[✓] Successfully saved student profile to data/students_db.json!")
    
    print("\n--- INGESTION SUMMARY ---")
    print(f"Student ID       : {profile.get('id')}")
    print(f"Student Name     : {profile.get('name')}")
    print(f"Class Level      : {profile.get('class_level')}")
    print(f"Board            : {profile.get('board')}")
    print(f"Board Subjects   : {', '.join(profile.get('board_subjects', []))}")
    print(f"Grade 10 Board   : {profile.get('grades', {}).get('g10_board', 'N/A')}")
    print(f"Grade 10 Subjects: {json.dumps(profile.get('grades', {}).get('g10_subjects', {}), indent=2)}")
    print(f"Standard Tests   : {json.dumps(profile.get('standardized_tests', {}))}")
    print(f"Portfolio Items  : {len(profile.get('portfolio', []))} activities/initiatives parsed.")
    for idx, item in enumerate(profile.get('portfolio', []), 1):
        print(f"   {idx}. [Tier {item.get('tier', 3)}] {item.get('activity')} — {item.get('description')[:70]}...")
    print(f"==================================================\n")
    
    return profile

def main():
    parser = argparse.ArgumentParser(description="Counselor Batch Student Data Ingestion Tool — unlockED")
    parser.add_argument("--file", "-f", nargs="+", help="Path to one or more student documents (PDF/TXT/DOCX)")
    parser.add_argument("--dir", "-d", help="Directory containing student documents to batch ingest")
    parser.add_argument("--name", "-n", help="Override student name")
    parser.add_argument("--interactive", "-i", action="store_true", help="Run interactive prompt for counselor ingestion")
    
    args = parser.parse_args()
    
    if args.file:
        ingest_student_documents(args.file, override_name=args.name)
    elif args.dir:
        dir_path = Path(args.dir)
        if not dir_path.is_dir():
            print(f"Error: {args.dir} is not a valid directory.")
            sys.exit(1)
        valid_exts = {".pdf", ".txt", ".docx"}
        files = [str(f) for f in dir_path.glob("*") if f.suffix.lower() in valid_exts]
        if not files:
            print(f"No PDF, TXT, or DOCX files found in {args.dir}.")
            sys.exit(1)
        print(f"Found {len(files)} student documents in {args.dir} for counselor ingestion.")
        for f in files:
            ingest_student_documents([f])
    elif args.interactive:
        print("--- Counselor Interactive Ingestion Mode ---")
        fpath = input("Enter path to student document (e.g. resume.pdf): ").strip()
        if os.path.exists(fpath):
            sname = input("Enter student name (or press Enter to auto-extract): ").strip()
            ingest_student_documents([fpath], override_name=sname if sname else None)
        else:
            print(f"File '{fpath}' not found.")
    else:
        parser.print_help()

if __name__ == "__main__":
    main()
