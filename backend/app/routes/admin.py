"""
Backend for the admin "Manage Teacher Accounts" and "Manage Subjects" pages.

GET    /teachers               -> list of professors (read-only, used for the name suggestions)
POST   /teachers               -> old mock-only "Add Teacher" form
DELETE /teachers/{teacher_id}  -> remove a teacher (mock-only)

GET    /teacher-accounts       -> list of teacher login accounts (users collection, role "Teacher")
POST   /teacher-accounts       -> "Create Account" form (professor + email + password)

GET    /subjects               -> list of subjects
POST   /subjects                -> "Add Subject" form
DELETE /subjects/{subject_code} -> remove a subject

GET    /assignments            -> list shown in the "Teacher Accounts" table
POST   /assignments             -> "Assign" button
DELETE /assignments/{assignment_id} -> X button next to an assignment row

IMPORTANT: professors, subjects, and schedules in iiti_db are all owned by
other systems/teams — even where a collection (like `subjects`) is
currently empty, it's still not ours to populate. So in real mode:
  - GET requests read the real data (safe, read-only)
  - POST/DELETE (writes) are NOT implemented against real MongoDB — they
    stay mock-only until the owning team confirms it's safe to write here.

Teacher accounts are the exception: they are new login documents in the
shared `users` collection (same shape as the existing Admin accounts, with
a `professorId` link). professors itself is never written to.
"""

from fastapi import APIRouter, Depends, HTTPException

from app.config import settings
from app.models.grade import (
    Teacher, TeacherCreate, TeacherAccount, TeacherAccountCreate,
    Subject, SubjectCreate, Assignment, AssignmentCreate,
)
from app.services import mock_data, mongo_repo
from app.database import get_db
from app.auth.dependencies import get_current_teacher, CurrentTeacher

router = APIRouter(tags=["admin"])


# --- Teachers ---

@router.get("/teachers", response_model=list[Teacher])
def list_teachers(current_teacher: CurrentTeacher = Depends(get_current_teacher)):
    if settings.USE_MOCK_DATA:
        return list(mock_data.MOCK_TEACHERS.values())
    return mongo_repo.list_teachers(get_db())  # read-only, safe


@router.post("/teachers", response_model=Teacher)
def add_teacher(payload: TeacherCreate, current_teacher: CurrentTeacher = Depends(get_current_teacher)):
    if not payload.full_name.strip():
        raise HTTPException(status_code=400, detail="Full name is required.")

    if settings.USE_MOCK_DATA:
        new_id = mock_data.next_teacher_id()
        teacher = Teacher(id=new_id, full_name=payload.full_name.strip())
        mock_data.MOCK_TEACHERS[new_id] = teacher
        return teacher

    raise HTTPException(
        status_code=501,
        detail="Teachers are managed elsewhere (professors collection) — adding here is not supported.",
    )


@router.delete("/teachers/{teacher_id}")
def delete_teacher(teacher_id: str, current_teacher: CurrentTeacher = Depends(get_current_teacher)):
    if settings.USE_MOCK_DATA:
        if teacher_id not in mock_data.MOCK_TEACHERS:
            raise HTTPException(status_code=404, detail="Teacher not found.")
        del mock_data.MOCK_TEACHERS[teacher_id]
        orphaned = [aid for aid, a in mock_data.MOCK_ASSIGNMENTS.items() if a.teacher_id == teacher_id]
        for aid in orphaned:
            del mock_data.MOCK_ASSIGNMENTS[aid]
        return {"deleted": True, "teacher_id": teacher_id}

    raise HTTPException(
        status_code=501,
        detail="Teachers are managed elsewhere (professors collection) — deleting here is not supported.",
    )


# --- Teacher accounts ---
# TODO: restrict these two routes to admins once real auth exists. Like every
# route in this file they only check the placeholder X-Teacher-Id header today,
# so any caller who sends that header can create accounts.

@router.get("/teacher-accounts", response_model=list[TeacherAccount])
def list_teacher_accounts(current_teacher: CurrentTeacher = Depends(get_current_teacher)):
    if settings.USE_MOCK_DATA:
        return list(mock_data.MOCK_TEACHER_ACCOUNTS.values())
    return mongo_repo.list_teacher_accounts(get_db())


@router.post("/teacher-accounts", response_model=TeacherAccount)
def create_teacher_account(payload: TeacherAccountCreate, current_teacher: CurrentTeacher = Depends(get_current_teacher)):
    email = payload.email.strip().lower()
    if "@" not in email or "." not in email.split("@")[-1]:
        raise HTTPException(status_code=400, detail="Enter a valid email address.")
    if len(payload.password.encode("utf-8")) > 72:
        raise HTTPException(status_code=400, detail="Password is too long (max 72 bytes).")

    if settings.USE_MOCK_DATA:
        teacher = mock_data.MOCK_TEACHERS.get(payload.professor_id)
        if not teacher:
            raise HTTPException(status_code=404, detail="Professor not found.")
        if any(a.email == email for a in mock_data.MOCK_TEACHER_ACCOUNTS.values()):
            raise HTTPException(status_code=409, detail="An account with this email already exists.")
        if any(a.professor_id == teacher.id for a in mock_data.MOCK_TEACHER_ACCOUNTS.values()):
            raise HTTPException(status_code=409, detail="This professor already has an account.")

        new_id = mock_data.next_teacher_account_id()
        account = TeacherAccount(
            id=new_id, professor_id=teacher.id, username=teacher.full_name,
            email=email, institute="IITI", role="Teacher",
        )
        mock_data.MOCK_TEACHER_ACCOUNTS[new_id] = account
        return account

    try:
        return mongo_repo.create_teacher_account(get_db(), payload.professor_id, email, payload.password)
    except LookupError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except ValueError as e:
        raise HTTPException(status_code=409, detail=str(e))


# --- Subjects ---
# Confirmed OK to write to real MongoDB — subjects collection is ours to
# manage (unlike professors/schedules, which stay read-only).

@router.get("/subjects", response_model=list[Subject])
def list_subjects(current_teacher: CurrentTeacher = Depends(get_current_teacher)):
    if settings.USE_MOCK_DATA:
        return list(mock_data.MOCK_SUBJECTS.values())
    return mongo_repo.list_subjects(get_db())


@router.post("/subjects", response_model=Subject)
def add_subject(payload: SubjectCreate, current_teacher: CurrentTeacher = Depends(get_current_teacher)):
    code = payload.code.strip().upper()
    title = payload.title.strip()

    if not code or not title:
        raise HTTPException(status_code=400, detail="Subject code and title are required.")

    if settings.USE_MOCK_DATA:
        if code in mock_data.MOCK_SUBJECTS:
            raise HTTPException(status_code=409, detail=f"Subject '{code}' already exists.")
        subject = Subject(code=code, title=title)
        mock_data.MOCK_SUBJECTS[code] = subject
        return subject

    try:
        return mongo_repo.add_subject(get_db(), code, title)
    except ValueError as e:
        raise HTTPException(status_code=409, detail=str(e))


@router.delete("/subjects/{subject_code}")
def delete_subject(subject_code: str, current_teacher: CurrentTeacher = Depends(get_current_teacher)):
    if settings.USE_MOCK_DATA:
        if subject_code not in mock_data.MOCK_SUBJECTS:
            raise HTTPException(status_code=404, detail="Subject not found.")
        del mock_data.MOCK_SUBJECTS[subject_code]
        orphaned = [aid for aid, a in mock_data.MOCK_ASSIGNMENTS.items() if a.subject_code == subject_code]
        for aid in orphaned:
            del mock_data.MOCK_ASSIGNMENTS[aid]
        return {"deleted": True, "subject_code": subject_code}

    deleted = mongo_repo.delete_subject(get_db(), subject_code)
    if not deleted:
        raise HTTPException(status_code=404, detail="Subject not found.")
    return {"deleted": True, "subject_code": subject_code}


# --- Assignments (still fully mock — no safe real backing yet) ---

@router.get("/assignments", response_model=list[Assignment])
def list_assignments(current_teacher: CurrentTeacher = Depends(get_current_teacher)):
    if settings.USE_MOCK_DATA:
        return list(mock_data.MOCK_ASSIGNMENTS.values())
    return mongo_repo.list_all_assignments(get_db())  # read-only, derived from schedules.classes


@router.post("/assignments", response_model=Assignment)
def add_assignment(payload: AssignmentCreate, current_teacher: CurrentTeacher = Depends(get_current_teacher)):
    if settings.USE_MOCK_DATA:
        teacher = mock_data.MOCK_TEACHERS.get(payload.teacher_id)
        if not teacher:
            raise HTTPException(status_code=404, detail="Teacher not found.")
        subject = mock_data.MOCK_SUBJECTS.get(payload.subject_code)
        if not subject:
            raise HTTPException(status_code=404, detail="Subject not found.")
        if not payload.section.strip():
            raise HTTPException(status_code=400, detail="Section is required.")

        new_id = mock_data.next_assignment_id()
        assignment = Assignment(
            id=new_id, teacher_id=teacher.id, teacher_name=teacher.full_name,
            subject_code=subject.code, subject_title=subject.title, section=payload.section.strip(),
        )
        mock_data.MOCK_ASSIGNMENTS[new_id] = assignment
        return assignment

    raise HTTPException(status_code=501, detail="Real assignment write not implemented yet.")


@router.delete("/assignments/{assignment_id}")
def delete_assignment(assignment_id: str, current_teacher: CurrentTeacher = Depends(get_current_teacher)):
    if settings.USE_MOCK_DATA:
        if assignment_id not in mock_data.MOCK_ASSIGNMENTS:
            raise HTTPException(status_code=404, detail="Assignment not found.")
        del mock_data.MOCK_ASSIGNMENTS[assignment_id]
        return {"deleted": True, "assignment_id": assignment_id}

    raise HTTPException(status_code=501, detail="Real assignment write not implemented yet.")