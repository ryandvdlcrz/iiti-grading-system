"""
GET  /sections/{section_id}/termgrades/csv?term=midterm -> Download CSV for
                                                             one term's components
POST /sections/{section_id}/termgrades/csv                -> Upload & Compute
                                                             (multipart: file + term)

CSV columns are DYNAMIC: "Student No.", "Name", then one column per
currently-configured grade component (e.g. "Quiz", "Exam", "Class
Participation", "Attendance" — whatever the admin has set up).

section_id now encodes the academic year + semester too (see
mongo_repo.make_section_id), so no extra term params are needed here —
look up once via get_section_by_id and everything downstream is already
scoped to the right term.
"""

import csv
import io

from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, Form
from fastapi.responses import StreamingResponse

from app.models.grade import TermComponents, StudentTermGradeRow
from app.services.grading import build_term_rows_from_stored
from app.services import mongo_repo
from app.database import get_db
from app.auth.dependencies import get_current_teacher, CurrentTeacher

router = APIRouter(prefix="/sections", tags=["termgrades-csv"])

FIXED_HEADERS = ["Student No.", "Name"]
VALID_TERMS = {"prelim", "midterm", "prefinal", "final"}
TERM_LABELS = {"prelim": "Prelim", "midterm": "Midterm", "prefinal": "PreFinal", "final": "Final"}


@router.get("/{section_id}/termgrades/csv")
def download_termgrades_csv(
    section_id: str,
    term: str,
    current_teacher: CurrentTeacher = Depends(get_current_teacher),
):
    if term not in VALID_TERMS:
        raise HTTPException(status_code=400, detail=f"Unknown term '{term}'. Must be one of: {', '.join(sorted(VALID_TERMS))}")

    db = get_db()
    lookup = mongo_repo.get_section_by_id(db, section_id)
    if not lookup:
        raise HTTPException(status_code=404, detail="Section not found.")

    section_name, subject_code, academic_year, semester = lookup

    try:
        students = mongo_repo.list_students_in_section(db, section_name)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

    term_data = mongo_repo.get_term_data_for_section(db, section_name, subject_code, academic_year, semester)
    grade_components = mongo_repo.list_grade_components(db)

    if not grade_components:
        raise HTTPException(status_code=400, detail="No grade components configured yet — set them up in Grade Components first.")

    headers = FIXED_HEADERS + [c.label for c in grade_components]

    buffer = io.StringIO()
    writer = csv.writer(buffer)
    writer.writerow(headers)

    for student in students:
        components = term_data.get(student.id, {}).get(term, TermComponents())
        row = [student.id, student.name]
        for component in grade_components:
            value = components.values.get(component.id)
            row.append(value if value is not None else "")
        writer.writerow(row)

    buffer.seek(0)
    term_slug = f"{academic_year}_{semester}".replace(" ", "")
    filename = f"{subject_code}_{section_name.replace(' ', '')}_{term_slug}_{TERM_LABELS[term]}_grades.csv"

    return StreamingResponse(
        iter([buffer.getvalue()]),
        media_type="text/csv",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )


@router.post("/{section_id}/termgrades/csv", response_model=list[StudentTermGradeRow])
async def upload_termgrades_csv(
    section_id: str,
    term: str = Form(...),
    file: UploadFile = File(...),
    current_teacher: CurrentTeacher = Depends(get_current_teacher),
):
    if term not in VALID_TERMS:
        raise HTTPException(status_code=400, detail=f"Unknown term '{term}'. Must be one of: {', '.join(sorted(VALID_TERMS))}")

    if not file.filename.lower().endswith(".csv"):
        raise HTTPException(status_code=400, detail="File must be a .csv")

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

    grade_components = mongo_repo.list_grade_components(db)

    if not grade_components:
        raise HTTPException(status_code=400, detail="No grade components configured yet — set them up in Grade Components first.")

    # Match uploaded column headers back to component ids by label. If the
    # admin renamed a component after this CSV was downloaded, its column
    # won't match anything here and will be silently ignored — matching the
    # same "unknown data is skipped" behavior as unknown student numbers.
    label_to_id = {c.label: c.id for c in grade_components}
    expected_headers = FIXED_HEADERS + list(label_to_id.keys())

    raw_bytes = await file.read()
    text = raw_bytes.decode("utf-8-sig")
    reader = csv.DictReader(io.StringIO(text))

    missing_cols = {"Student No.", "Name"} - set(reader.fieldnames or [])
    if missing_cols:
        raise HTTPException(status_code=400, detail=f"CSV is missing expected columns: {', '.join(sorted(missing_cols))}")

    def parse_num(value: str):
        value = (value or "").strip()
        if value == "":
            return None
        try:
            return float(value)
        except ValueError:
            return None

    try:
        students = mongo_repo.list_students_in_section(db, section_name)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

    known_student_ids = {s.id for s in students}
    updated_components: dict[str, TermComponents] = {}

    for row in reader:
        student_id = row.get("Student No.", "").strip()
        if student_id not in known_student_ids:
            continue

        values = {}
        for label, component_id in label_to_id.items():
            if label in row:
                parsed = parse_num(row[label])
                if parsed is not None:
                    values[component_id] = parsed

        updated_components[student_id] = TermComponents(values=values)

    mongo_repo.save_term_components(db, section_name, subject_code, academic_year, semester, term, updated_components)

    full_data = mongo_repo.get_full_grades_for_section(db, section_name, subject_code, academic_year, semester)
    return build_term_rows_from_stored(students, full_data)