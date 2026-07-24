import re

class BoardGradeConverter:
    """
    Standardized Inter-Board Grade Conversion Engine for Grade 10 & Grade 12.
    Converts letter grades, points, and descriptors from IGCSE, IB MYP, IBDP, A-Levels,
    ICSE, ISC, and CBSE into standardized percentage equivalents and performance levels.
    """

    # Grade 10 Conversions
    G10_TABLE = [
        {
            "level": "Outstanding",
            "igcse": ["9", "8", "a*", "astar"],
            "ib_myp": [7],
            "icse_pct": 95.0,
            "cbse_pct": 95.0,
            "cbse_grade": ["a1"]
        },
        {
            "level": "Excellent",
            "igcse": ["7", "a"],
            "ib_myp": [6],
            "icse_pct": 85.0,
            "cbse_pct": 85.0,
            "cbse_grade": ["a2"]
        },
        {
            "level": "Very Good",
            "igcse": ["6", "5", "b"],
            "ib_myp": [5],
            "icse_pct": 75.0,
            "cbse_pct": 75.0,
            "cbse_grade": ["b1"]
        },
        {
            "level": "Good",
            "igcse": ["4", "c"],
            "ib_myp": [4],
            "icse_pct": 65.0,
            "cbse_pct": 65.0,
            "cbse_grade": ["b2"]
        },
        {
            "level": "Satisfactory",
            "igcse": ["3", "d"],
            "ib_myp": [3],
            "icse_pct": 55.0,
            "cbse_pct": 55.0,
            "cbse_grade": ["c1"]
        },
        {
            "level": "Pass",
            "igcse": ["2", "1", "e", "f", "g"],
            "ib_myp": [2],
            "icse_pct": 40.0,
            "cbse_pct": 40.0,
            "cbse_grade": ["c2", "d"]
        },
        {
            "level": "Fail",
            "igcse": ["u"],
            "ib_myp": [1],
            "icse_pct": 20.0,
            "cbse_pct": 20.0,
            "cbse_grade": ["e"]
        }
    ]

    # Grade 12 Conversions
    G12_TABLE = [
        {
            "level": "Outstanding",
            "ibdp": [7],
            "a_levels": ["a*", "astar"],
            "isc_pct": 97.5,
            "cbse_pct": 95.0,
            "cbse_grade": ["a1"]
        },
        {
            "level": "Excellent",
            "ibdp": [6],
            "a_levels": ["a"],
            "isc_pct": 92.0,
            "cbse_pct": 85.0,
            "cbse_grade": ["a2"]
        },
        {
            "level": "Very Good",
            "ibdp": [5],
            "a_levels": ["b"],
            "isc_pct": 85.0,
            "cbse_pct": 75.0,
            "cbse_grade": ["b1"]
        },
        {
            "level": "Good",
            "ibdp": [4],
            "a_levels": ["c"],
            "isc_pct": 75.0,
            "cbse_pct": 65.0,
            "cbse_grade": ["b2"]
        },
        {
            "level": "Satisfactory",
            "ibdp": [3],
            "a_levels": ["d"],
            "isc_pct": 65.0,
            "cbse_pct": 55.0,
            "cbse_grade": ["c1"]
        },
        {
            "level": "Pass",
            "ibdp": [2],
            "a_levels": ["e"],
            "isc_pct": 50.0,
            "cbse_pct": 40.0,
            "cbse_grade": ["c2", "d"]
        },
        {
            "level": "Fail",
            "ibdp": [1],
            "a_levels": ["u"],
            "isc_pct": 20.0,
            "cbse_pct": 20.0,
            "cbse_grade": ["e"]
        }
    ]

    @classmethod
    def convert_grade(cls, raw_grade, class_level=12, board="CBSE"):
        """
        Converts any grade input (e.g. 'A*', '7', '95%', 'A1') into a standardized
        equivalent percentage float and performance level descriptor.
        """
        if raw_grade is None:
            return None, None

        val_str = str(raw_grade).strip().lower()
        clean_val = val_str.replace("grade", "").replace("level", "").replace("*", "star").strip()

        # Check if already numeric float/pct
        numeric_m = re.search(r"(\d+(?:\.\d+)?)\%?", val_str)
        numeric_val = float(numeric_m.group(1)) if numeric_m else None

        table = cls.G10_TABLE if int(class_level) == 10 else cls.G12_TABLE

        # Direct match search in conversion table
        for row in table:
            # Match IGCSE / A Levels / IB / CBSE Grade
            candidates = []
            if "igcse" in row: candidates.extend(row["igcse"])
            if "a_levels" in row: candidates.extend(row["a_levels"])
            if "ib_myp" in row: candidates.extend([str(x) for x in row["ib_myp"]])
            if "ibdp" in row: candidates.extend([str(x) for x in row["ibdp"]])
            if "cbse_grade" in row: candidates.extend(row["cbse_grade"])

            if clean_val in candidates or val_str in candidates:
                # Return standard percentage equivalent
                pct_equiv = row.get("cbse_pct") or row.get("icse_pct") or row.get("isc_pct", 85.0)
                return pct_equiv, row["level"]

        # If numeric value provided (e.g. 92.5%), map to level & standardized percentage
        if numeric_val is not None:
            if numeric_val <= 7 and numeric_val >= 1: # IB scale
                for row in table:
                    ib_vals = row.get("ib_myp", []) + row.get("ibdp", [])
                    if int(numeric_val) in ib_vals:
                        return row.get("cbse_pct", 85.0), row["level"]

            # Direct percentage
            for row in table:
                target_pct = row.get("cbse_pct") or row.get("isc_pct") or 50.0
                if numeric_val >= (target_pct - 5.0):
                    return numeric_val, row["level"]

            return numeric_val, "Custom"

        # Fallback default if unmapped letter
        if "a" in clean_val:
            return 90.0, "Excellent"
        elif "b" in clean_val:
            return 75.0, "Very Good"
        elif "c" in clean_val:
            return 65.0, "Good"
        elif "d" in clean_val:
            return 55.0, "Satisfactory"

        return 80.0, "Standardized"

    @classmethod
    def standardize_profile_grades(cls, profile):
        """
        Takes a student profile dict and normalizes all raw subject grades and
        expected board aggregates into standard numeric percentages using the conversion tables.
        """
        class_lvl = int(profile.get("class_level", 12))
        board = profile.get("board", "CBSE")
        grades = profile.get("grades", {})
        subjects_grades = grades.get("subjects", {})

        standardized_subjects = {}
        pct_list = []

        for sub_name, raw_g in subjects_grades.items():
            pct_val, level = cls.convert_grade(raw_g, class_level=class_lvl, board=board)
            if pct_val is not None:
                standardized_subjects[sub_name] = pct_val
                pct_list.append(pct_val)
            else:
                standardized_subjects[sub_name] = raw_g

        profile["grades"]["subjects"] = standardized_subjects

        # Standardize expected board aggregate
        exp_board = grades.get("current_expected_board")
        if exp_board:
            exp_pct, _ = cls.convert_grade(exp_board, class_level=class_lvl, board=board)
            if exp_pct is not None:
                profile["grades"]["current_expected_board"] = f"{exp_pct:.1f}%"
        elif pct_list:
            avg_pct = sum(pct_list) / len(pct_list)
            profile["grades"]["current_expected_board"] = f"{avg_pct:.1f}%"

        return profile
