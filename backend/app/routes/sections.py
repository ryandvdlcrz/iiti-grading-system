"""
GET /sections       -> sections assigned to the logged-in teacher, optionally
                        scoped to one academic year + semester
GET /sections/terms -> distinct academic year + semester combinations found
                        across all schedules, latest first (used to populate
                        the term dropdown on both the teacher Grade page and
                        the admin View Grade page)

Mock mode: served from app.services.mock_data.
Real mode: served from iiti_db via app.services.mongo_repo — professors,
schedules, and students are READ-ONLY here (owned by the other team's
system).
"""

from fastapi import APIRouter, Depends

from app.config import settings
from app.models.grade import Section, Term
from app.services import mock_data, mongo_repo
from app.database import get_db
from app.auth.dependencies import get_current_teacher, CurrentTeacher

router = APIRouter(prefix="/sections", tags=["sections"])


@router.get("", response_model=list[Section])
def list_sections(
    academic_year: str | None = None,
    semester: str | None = None,
    current_teacher: CurrentTeacher = Depends(get_current_teacher),
):
    if settings.USE_MOCK_DATA:
        return list(mock_data.MOCK_SECTIONS.values())

    db = get_db()
    return mongo_repo.list_sections_for_teacher(db, current_teacher.teacher_id, academic_year, semester)


@router.get("/terms", response_model=list[Term])
def list_terms(current_teacher: CurrentTeacher = Depends(get_current_teacher)):
    if settings.USE_MOCK_DATA:
        return []
    return mongo_repo.list_available_terms(get_db())