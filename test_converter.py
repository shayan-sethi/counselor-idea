import sys
from prism_agent.board_converter import BoardGradeConverter

def test_conversions():
    print("====================================================")
    print("INTER-BOARD CONVERSION MODULE UNIT TEST")
    print("====================================================")

    # Test Case 1: Grade 10 IGCSE A* in Physics
    pct, level = BoardGradeConverter.convert_grade("A*", class_level=10, board="IGCSE")
    print(f"Grade 10 IGCSE A* -> {pct}% ({level})")
    assert pct == 95.0, f"Expected 95.0, got {pct}"

    # Test Case 2: Grade 10 IB MYP 7
    pct, level = BoardGradeConverter.convert_grade(7, class_level=10, board="IB MYP")
    print(f"Grade 10 IB MYP 7 -> {pct}% ({level})")
    assert pct == 95.0, f"Expected 95.0, got {pct}"

    # Test Case 3: Grade 12 A Levels A*
    pct, level = BoardGradeConverter.convert_grade("A*", class_level=12, board="A Levels")
    print(f"Grade 12 A Levels A* -> {pct}% ({level})")
    assert pct == 95.0, f"Expected 95.0, got {pct}"

    # Test Case 4: Grade 12 IBDP 6
    pct, level = BoardGradeConverter.convert_grade(6, class_level=12, board="IBDP")
    print(f"Grade 12 IBDP 6 -> {pct}% ({level})")
    assert pct == 85.0 or pct == 92.0 or pct == 85.0, f"Expected Excellent range, got {pct}"

    # Test Case 5: Standardizing full profile
    profile = {
        "class_level": 10,
        "board": "IGCSE",
        "grades": {
            "subjects": {
                "Physics": "A*",
                "Mathematics": "8",
                "Chemistry": "A",
                "English": "B"
            }
        }
    }
    std_prof = BoardGradeConverter.standardize_profile_grades(profile)
    print("\nStandardized Grade 10 Profile:")
    print(std_prof["grades"])

    assert std_prof["grades"]["subjects"]["Physics"] == 95.0
    assert std_prof["grades"]["subjects"]["Mathematics"] == 95.0
    assert std_prof["grades"]["subjects"]["Chemistry"] == 85.0
    assert std_prof["grades"]["subjects"]["English"] == 75.0

    print("\n====================================================")
    print("[✔] ALL INTER-BOARD CONVERSION TESTS PASSED!")
    print("====================================================")

if __name__ == "__main__":
    test_conversions()
