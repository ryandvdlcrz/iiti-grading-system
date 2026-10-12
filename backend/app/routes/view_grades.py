"""
Backend for the admin "View Grade" page. Strictly read-only: reuses the
same grades data and 30/70 cascade formula as the teacher's Overall view,
now scoped to a specific academic year + semester so history from past
terms stays separate from the current one.

GET /view-grades/filter-options -> populate the dropdowns (Course, Year
                                     Level, Section, Subject, Term)
GET /view-grades                -> table rows, two modes:
                                     - year_level + section given: full
                                       class ledger for that section
                                     - q given (no year_level/section):
                                       case-insensitive name/number search
                                       across every section that teaches
                                       subject_code in that term
GET /view-grades/csv             -> same rows as a CSV download, same modes

subject_code, academic_year and semester are always required — a subject
only belongs to one year level within a given term, so the search bar
only makes sense once a subject (and term) is picked.
"""

import csv
import io

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import StreamingResponse

from app.models.grade import ViewGradeRow, ViewGradeFilterOptions
from app.services.grading import build_view_grade_rows_from_stored
from app.services import mongo_repo
from app.database import get_db
from app.auth.dependencies import get_current_teacher, CurrentTeacher

router = APIRouter(prefix="/view-grades", tags=["view-grades"])

CSV_HEADERS = [
    "Student No.", "Name", "Prelim", "Raw Midterm", "Midterm",
    "Raw Pre-Final", "Pre-Final", "Raw Final", "Final", "Equivalent",
]


@router.get("/filter-options", response_model=ViewGradeFilterOptions)
def get_filter_options(
    year_level: str | None = None,
    section: str | None = None,
    academic_year: str | None = None,
    semester: str | None = None,
    current_teacher: CurrentTeacher = Depends(get_current_teacher),
):
    return mongo_repo.list_view_grade_filter_options(get_db(), year_level, section, academic_year, semester)


def _resolve_class_rows(db, year_level: str, section: str, subject_code: str, academic_year: str, semester: str) -> list[ViewGradeRow]:
    section_name = f"BSIT-{year_level}{section}"
    students = mongo_repo.list_students_in_section_view(db, section_name)
    if not students:
        return []

    full_data = mongo_repo.get_full_grades_for_section(db, section_name, subject_code, academic_year, semester)
    return build_view_grade_rows_from_stored(students, full_data, section=section_name)


def _resolve_search_rows(db, subject_code: str, academic_year: str, semester: str, query: str) -> list[ViewGradeRow]:
    matches = mongo_repo.find_students_by_subject_and_query(db, subject_code, academic_year, semester, query)
    if not matches:
        return []

    by_section: dict[str, list] = {}
    for student, section_name in matches:
        by_section.setdefault(section_name, []).append(student)

    rows: list[ViewGradeRow] = []
    for section_name, students in by_section.items():
        full_data = mongo_repo.get_full_grades_for_section(db, section_name, subject_code, academic_year, semester)
        rows.extend(build_view_grade_rows_from_stored(students, full_data, section=section_name))
    return rows


def _resolve_rows(
    db, subject_code: str, academic_year: str, semester: str, year_level: str | None, section: str | None, q: str | None
) -> list[ViewGradeRow]:
    if year_level and section:
        return _resolve_class_rows(db, year_level, section, subject_code, academic_year, semester)
    if q:
        return _resolve_search_rows(db, subject_code, academic_year, semester, q)
    raise HTTPException(status_code=400, detail="Provide either year_level + section, or a search query q.")


@router.get("", response_model=list[ViewGradeRow])
def get_view_grades(
    subject_code: str,
    academic_year: str,
    semester: str,
    course: str = "BSIT",
    year_level: str | None = None,
    section: str | None = None,
    q: str | None = None,
    current_teacher: CurrentTeacher = Depends(get_current_teacher),
):
    return _resolve_rows(get_db(), subject_code, academic_year, semester, year_level, section, q)


@router.get("/csv")
def download_view_grades_csv(
    subject_code: str,
    academic_year: str,
    semester: str,
    course: str = "BSIT",
    year_level: str | None = None,
    section: str | None = None,
    q: str | None = None,
    current_teacher: CurrentTeacher = Depends(get_current_teacher),
):
    rows = _resolve_rows(get_db(), subject_code, academic_year, semester, year_level, section, q)

    buffer = io.StringIO()
    writer = csv.writer(buffer)
    writer.writerow(CSV_HEADERS)
    for r in rows:
        writer.writerow([
            r.id, r.name, r.prelim, r.raw_midterm, r.midterm,
            r.raw_prefinal, r.prefinal, r.raw_final, r.final, r.equivalent,
        ])
    buffer.seek(0)

    term_slug = f"{academic_year}_{semester}".replace(" ", "")
    if year_level and section:
        filename = f"BSIT-{year_level}{section}_{subject_code}_{term_slug}_grades.csv"
    else:
        filename = f"{subject_code}_{term_slug}_search_grades.csv"

    return StreamingResponse(
        iter([buffer.getvalue()]),
        media_type="text/csv",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )