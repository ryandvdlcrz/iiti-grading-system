from typing import Optional
from app.models.grade import (
    Student, TermComponents, StudentTermGradeRow, GradeComponent, ViewGradeRow,
)

# --- Term-based component grading (Grade Components admin page) ---

GRADE_EQUIVALENT_TABLE = [
    (99, 1.00),
    (96, 1.25),
    (93, 1.50),
    (90, 1.75),
    (87, 2.00),
    (84, 2.25),
    (81, 2.50),
    (77, 2.75),
    (75, 3.00),
]


def compute_term_raw(
    components: TermComponents,
    grade_components: list[GradeComponent],
    round_to: int = 2,
) -> Optional[float]:
    """
    Weighted sum of the student's scores using the CURRENT admin-defined
    grade components (label + percentage). Returns None if there are no
    grade components configured, or the student is missing a score for
    any configured component (can't compute a partial term).
    """
    if not grade_components:
        return None

    total = 0.0
    for component in grade_components:
        value = components.values.get(component.id)
        if value is None:
            return None
        total += value * (component.percentage / 100)

    return round(total, round_to)


def get_grade_equivalent(final_percentage: Optional[float]) -> Optional[float]:
    if final_percentage is None:
        return None
    for min_percentage, equivalent in GRADE_EQUIVALENT_TABLE:
        if final_percentage >= min_percentage:
            return equivalent
    return 5.00


# --- Reading back what was saved ---
# IMPORTANT: these do NOT recompute anything from grade_components. Each
# term's raw value, and the full cascade built from them, is frozen onto
# the document at save time (see mongo_repo.save_term_components) using
# whatever grade components were configured AT THAT MOMENT. That snapshot
# is the permanent historical record — these functions just read it back.
# This is what keeps a graduated student's old grades from silently
# changing if the admin later edits or deletes a grade component.

def build_term_rows_from_stored(
    students: list[Student],
    full_data: dict[str, dict],
) -> list[StudentTermGradeRow]:
    rows = []
    for student in students:
        data = full_data.get(student.id, {})
        components = data.get("components", {})
        computed = data.get("computed") or {}
        rows.append(StudentTermGradeRow(
            id=student.id,
            name=student.name,
            prelimComponents=components.get("prelim", TermComponents()),
            midtermComponents=components.get("midterm", TermComponents()),
            prefinalComponents=components.get("prefinal", TermComponents()),
            finalComponents=components.get("final", TermComponents()),
            prelim=computed.get("prelim"),
            midterm=computed.get("midterm"),
            prefinal=computed.get("prefinal"),
            final=computed.get("final"),
            equivalent=computed.get("equivalent"),
        ))
    return rows


def build_view_grade_rows_from_stored(
    students: list[Student],
    full_data: dict[str, dict],
    section: Optional[str] = None,
) -> list[ViewGradeRow]:
    rows = []
    for student in students:
        data = full_data.get(student.id, {})
        computed = data.get("computed") or {}
        rows.append(ViewGradeRow(
            id=student.id,
            name=student.name,
            section=section,
            prelim=computed.get("prelim"),
            raw_midterm=computed.get("raw_midterm"),
            midterm=computed.get("midterm"),
            raw_prefinal=computed.get("raw_prefinal"),
            prefinal=computed.get("prefinal"),
            raw_final=computed.get("raw_final"),
            final=computed.get("final"),
            equivalent=computed.get("equivalent"),
        ))
    return rows