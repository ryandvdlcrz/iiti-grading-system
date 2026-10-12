"""
GET /me -> resolves the current placeholder-auth teacher id (X-Teacher-Id
header) into a full Teacher record {id, full_name}.

Mock mode: X-Teacher-Id must be one of t1-t4 (see mock_data.py).
Real mode: X-Teacher-Id must be a real professors._id from iiti_db.
"""

from fastapi import APIRouter, Depends, HTTPException

from app.config import settings
from app.models.grade import Teacher
from app.services import mongo_repo
from app.database import get_db
from app.auth.dependencies import get_current_teacher, CurrentTeacher

router = APIRouter(tags=["me"])


@router.get("/me", response_model=Teacher)
def get_me(current_teacher: CurrentTeacher = Depends(get_current_teacher)):
    if settings.USE_MOCK_DATA:
        from app.services import mock_data
        teacher = mock_data.MOCK_TEACHERS.get(current_teacher.teacher_id)
        if not teacher:
            raise HTTPException(
                status_code=404,
                detail=f"No teacher found for id '{current_teacher.teacher_id}'. "
                       f"Use one of: {', '.join(mock_data.MOCK_TEACHERS.keys())}",
            )
        return teacher

    db = get_db()
    teacher = mongo_repo.get_teacher_by_id(db, current_teacher.teacher_id)
    if not teacher:
        raise HTTPException(
            status_code=404,
            detail=f"No professor found for id '{current_teacher.teacher_id}' in iiti_db.",
        )
    return teacher