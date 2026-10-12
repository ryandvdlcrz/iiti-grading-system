from app.models.grade import Student, GradeInput
from app.services.grading import compute_row, is_failing


def test_full_cascade_matches_manual_calculation():
    student = Student(id="20210009", name="Ryan Dela Cruz")
    grade_input = GradeInput(prelim=85, rawMid=88, rawPre=90, rawFinal=87)

    row = compute_row(student, grade_input)

    assert row.midterm == 87.1     # 0.30*85 + 0.70*88
    assert row.prefinal == 89.13   # 0.30*87.1 + 0.70*90
    assert row.final == 87.64      # 0.30*89.13 + 0.70*87 -> 87.639 rounded


def test_partial_data_leaves_downstream_fields_none():
    student = Student(id="202410099", name="Incomplete Student")
    grade_input = GradeInput(prelim=90)  # no raw midterm yet

    row = compute_row(student, grade_input)

    assert row.midterm is None
    assert row.prefinal is None
    assert row.final is None


def test_is_failing_threshold():
    assert is_failing(74.9) is True
    assert is_failing(75) is False
    assert is_failing(None) is False