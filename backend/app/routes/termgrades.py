"""
GET  /sections/{section_id}/termgrades -> full class ledger: per-term raw
                                            components (for editing) plus
                                            the FROZEN cascade snapshot
                                            (Prelim -> Final -> Equivalent)
POST /sections/{section_id}/termgrades -> save one term's components for
                                            some/all students, re-freezes
                                            that term's raw value and
                                            rebuilds the cascade from
                                            whatever raw snapshots exist

Uses the admin-configurable grade components (Grade Components page)
instead of fixed Quiz/CP/Attendance/Exam weights. Both routes read from
the stored `computedGrades` snapshot (see mongo_repo.save_term_components)
rather than recomputing the cascade live — this is what keeps a term's
official grade stable even if the admin later edits or deletes a grade
component, since only re-saving that specific term changes its frozen
raw value.

section_id now encodes the academic year + semester too (see
mongo_repo.make_section_id), so no extra term params are needed on these
routes — look up once via get_section_by_id and everything downstream is
already scoped correctly.
"""

from fastapi import APIRouter, Depends, HTTPException

from app.config import settings
from app.models.grade import SaveTermGradesRequest, StudentTermGradeRow
from app.services.grading import build_term_rows_from_stored
from app.services import mongo_repo
from app.database import get_db
from app.auth.dependencies import get_current_teacher, CurrentTeacher

router = APIRouter(prefix="/sections", tags=["termgrades"])

VALID_TERMS = {"prelim", "midterm", "prefinal", "final"}


@router.get("/{section_id}/termgrades", response_model=list[StudentTermGradeRow])
def get_term_grades(section_id: str, current_teacher: CurrentTeacher = Depends(get_current_teacher)):
    if settings.USE_MOCK_DATA:
        raise HTTPException(status_code=501, detail="Mock mode not implemented for termgrades yet.")

    db = get_db()

    lookup = mongo_repo.get_section_by_id(db, section_id)
    if not lookup:
        raise HTTPException(status_code=404, detail="Section not found.")

    section_name, subject_code, academic_year, semester = lookup

    try:
        students = mongo_repo.list_students_in_section(db, section_name)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

    full_data = mongo_repo.get_full_grades_for_section(db, section_name, subject_code, academic_year, semester)

    return build_term_rows_from_stored(students, full_data)


@router.post("/{section_id}/termgrades", response_model=list[StudentTermGradeRow])
def save_term_grades(
    section_id: str,
    payload: SaveTermGradesRequest,
    current_teacher: CurrentTeacher = Depends(get_current_teacher),
):
    if payload.term not in VALID_TERMS:
        raise HTTPException(
            status_code=400,
            detail=f"Unknown term '{payload.term}'. Must be one of: {', '.join(sorted(VALID_TERMS))}",
        )

    if settings.USE_MOCK_DATA:
        raise HTTPException(status_code=501, detail="Mock mode not implemented for termgrades yet.")

    db = get_db()
    lookup = mongo_repo.get_section_by_id(db, section_id)
    if not lookup:
        raise HTTPException(status_code=404, detail="Section not found.")

    section_name, subject_code, academic_year, semester = lookup

    if not mongo_repo.is_term_current(db, academic_year, semester):
        raise HTTPException(
            status_code=403,
            detail="This semester has ended and its grades are locked. Contact an admin if a correction is needed.",
        )

    mongo_repo.save_term_components(db, section_name, subject_code, academic_year, semester, payload.term, payload.components)

    try:
        students = mongo_repo.list_students_in_section(db, section_name)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

    full_data = mongo_repo.get_full_grades_for_section(db, section_name, subject_code, academic_year, semester)

    return build_term_rows_from_stored(students, full_data)