"""
Backend for the admin "Grade Components" page.

GET    /grade-components            -> list current components
POST   /grade-components             -> "Add" button
PATCH  /grade-components/{id}        -> edit a component's label/percentage
DELETE /grade-components/{id}        -> "X" button, remove a component

Global — one set of components shared across every subject/section
(confirmed with the user). New collection: `grading_components`.
"""

from fastapi import APIRouter, Depends, HTTPException

from app.models.grade import GradeComponent, GradeComponentCreate, GradeComponentUpdate
from app.services import mongo_repo
from app.database import get_db
from app.auth.dependencies import get_current_teacher, CurrentTeacher

router = APIRouter(prefix="/grade-components", tags=["grade-components"])


@router.get("", response_model=list[GradeComponent])
def list_grade_components(current_teacher: CurrentTeacher = Depends(get_current_teacher)):
    return mongo_repo.list_grade_components(get_db())


@router.post("", response_model=GradeComponent)
def add_grade_component(payload: GradeComponentCreate, current_teacher: CurrentTeacher = Depends(get_current_teacher)):
    label = payload.label.strip()
    if not label:
        raise HTTPException(status_code=400, detail="Label is required.")

    return mongo_repo.add_grade_component(get_db(), label, payload.percentage)


@router.patch("/{component_id}", response_model=GradeComponent)
def update_grade_component(
    component_id: str,
    payload: GradeComponentUpdate,
    current_teacher: CurrentTeacher = Depends(get_current_teacher),
):
    label = payload.label.strip() if payload.label is not None else None
    if label is not None and not label:
        raise HTTPException(status_code=400, detail="Label cannot be empty.")

    updated = mongo_repo.update_grade_component(get_db(), component_id, label, payload.percentage)
    if not updated:
        raise HTTPException(status_code=404, detail="Grade component not found.")
    return updated


@router.delete("/{component_id}")
def delete_grade_component(component_id: str, current_teacher: CurrentTeacher = Depends(get_current_teacher)):
    deleted = mongo_repo.delete_grade_component(get_db(), component_id)
    if not deleted:
        raise HTTPException(status_code=404, detail="Grade component not found.")
    return {"deleted": True, "component_id": component_id}