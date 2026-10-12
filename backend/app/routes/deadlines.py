"""
Backend for deadlineAndReminders.jsx.

GET  /deadlines              -> current deadline (if any) for every term
POST /deadlines               -> "Save" button — set/update deadline for one term
POST /reminders/send          -> "Send Reminder Now" — logs a reminder AND
                                  creates a real teacher-facing notification
GET  /reminders/log           -> "Reminder Log" list, newest first

Mock mode: served from mock_data.
Real mode: served from iiti_db via mongo_repo — new `grading_deadlines` and
`grading_reminder_log` collections (both ours; not the shared `systemsettings`
collection, which something else currently uses).
"""

from datetime import datetime, timezone
from fastapi import APIRouter, Depends, HTTPException

from app.config import settings
from app.models.grade import Deadline, DeadlineSet, SendReminderRequest, ReminderLogEntry
from app.services import mongo_repo
from app.database import get_db
from app.auth.dependencies import get_current_teacher, CurrentTeacher

router = APIRouter(tags=["deadlines"])


@router.get("/deadlines", response_model=list[Deadline])
def list_deadlines(current_teacher: CurrentTeacher = Depends(get_current_teacher)):
    if settings.USE_MOCK_DATA:
        from app.services import mock_data
        return list(mock_data.MOCK_DEADLINES.values())

    return mongo_repo.list_deadlines(get_db())


@router.post("/deadlines", response_model=Deadline)
def set_deadline(payload: DeadlineSet, current_teacher: CurrentTeacher = Depends(get_current_teacher)):
    if settings.USE_MOCK_DATA:
        from app.services import mock_data
        if payload.term not in mock_data.TERMS:
            raise HTTPException(status_code=400, detail=f"Unknown term '{payload.term}'.")
        deadline = Deadline(term=payload.term, deadline_date=payload.deadline_date)
        mock_data.MOCK_DEADLINES[payload.term] = deadline
        return deadline

    if payload.term not in mongo_repo.TERMS:
        raise HTTPException(
            status_code=400,
            detail=f"Unknown term '{payload.term}'. Must be one of: {', '.join(mongo_repo.TERMS)}",
        )
    return mongo_repo.set_deadline(get_db(), payload.term, payload.deadline_date)


@router.post("/reminders/send", response_model=ReminderLogEntry)
def send_reminder(payload: SendReminderRequest, current_teacher: CurrentTeacher = Depends(get_current_teacher)):
    if settings.USE_MOCK_DATA:
        from app.services import mock_data
        if payload.term not in mock_data.TERMS:
            raise HTTPException(status_code=400, detail=f"Unknown term '{payload.term}'.")

        teacher_count = len({a.teacher_id for a in mock_data.MOCK_ASSIGNMENTS.values()})
        entry = ReminderLogEntry(
            id=mock_data.next_reminder_id(), term=payload.term, teacher_count=teacher_count,
            sent_at=datetime.now(timezone.utc).strftime("%b %d, %Y %I:%M %p") + " UTC", status="SENT",
        )
        mock_data.MOCK_REMINDER_LOG.insert(0, entry)

        deadline = mock_data.MOCK_DEADLINES.get(payload.term)
        deadline_text = f" Due {deadline.deadline_date}." if deadline and deadline.deadline_date else ""
        notif_id = mock_data.next_notification_id()
        from app.models.grade import NotificationItem
        notification = NotificationItem(
            id=notif_id,
            message=f"{payload.term} grades are due soon — please submit on time.{deadline_text}",
            time=datetime.now(timezone.utc).strftime("%b %d, %I:%M %p"), unread=True,
        )
        mock_data.MOCK_NOTIFICATIONS[notif_id] = notification
        return entry

    if payload.term not in mongo_repo.TERMS:
        raise HTTPException(
            status_code=400,
            detail=f"Unknown term '{payload.term}'. Must be one of: {', '.join(mongo_repo.TERMS)}",
        )

    db = get_db()
    teacher_count = mongo_repo.get_active_teacher_count(db)
    sent_at = datetime.now(timezone.utc).strftime("%b %d, %Y %I:%M %p") + " UTC"
    entry = mongo_repo.add_reminder_log_entry(db, payload.term, teacher_count, sent_at)

    deadlines = {d.term: d.deadline_date for d in mongo_repo.list_deadlines(db)}
    deadline_date = deadlines.get(payload.term)
    deadline_text = f" Due {deadline_date}." if deadline_date else ""
    notif_time = datetime.now(timezone.utc).strftime("%b %d, %I:%M %p")
    mongo_repo.add_notification(
        db,
        f"{payload.term} grades are due soon — please submit on time.{deadline_text}",
        notif_time,
    )

    return entry


@router.get("/reminders/log", response_model=list[ReminderLogEntry])
def get_reminder_log(current_teacher: CurrentTeacher = Depends(get_current_teacher)):
    if settings.USE_MOCK_DATA:
        from app.services import mock_data
        return mock_data.MOCK_REMINDER_LOG

    return mongo_repo.list_reminder_log(get_db())