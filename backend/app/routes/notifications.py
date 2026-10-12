"""
Backend for notifications.jsx.

GET  /notifications              -> list of notifications
POST /notifications/{id}/read    -> mark a single notification as read

Mock mode: served from mock_data.MOCK_NOTIFICATIONS.
Real mode: served from a dedicated `grading_notifications` collection in
iiti_db — deliberately NOT the existing `notifications` collection, which
belongs to the enrollment system and has its own schema/purpose.
"""

from fastapi import APIRouter, Depends, HTTPException

from datetime import datetime, timezone

from app.config import settings
from app.models.grade import NotificationItem, NotificationCreate
from app.services import mongo_repo
from app.database import get_db
from app.auth.dependencies import get_current_teacher, CurrentTeacher

router = APIRouter(prefix="/notifications", tags=["notifications"])


@router.get("", response_model=list[NotificationItem])
def list_notifications(current_teacher: CurrentTeacher = Depends(get_current_teacher)):
    if settings.USE_MOCK_DATA:
        from app.services import mock_data
        return list(mock_data.MOCK_NOTIFICATIONS.values())

    return mongo_repo.list_notifications(get_db())


@router.post("", response_model=NotificationItem)
def create_notification(payload: NotificationCreate, current_teacher: CurrentTeacher = Depends(get_current_teacher)):
    """
    Creates a new notification. Used for testing/demo right now — this is
    also the same function a future 'Send Reminder Now' real-mode handler
    would call once Deadlines & Reminders is wired to MongoDB.
    """
    time_str = datetime.now(timezone.utc).strftime("%b %d, %I:%M %p")

    if settings.USE_MOCK_DATA:
        from app.services import mock_data
        new_id = mock_data.next_notification_id()
        notification = NotificationItem(id=new_id, message=payload.message, time=time_str, unread=True)
        mock_data.MOCK_NOTIFICATIONS[new_id] = notification
        return notification

    return mongo_repo.add_notification(get_db(), payload.message, time_str)


@router.post("/{notification_id}/read", response_model=NotificationItem)
def mark_notification_read(notification_id: str, current_teacher: CurrentTeacher = Depends(get_current_teacher)):
    if settings.USE_MOCK_DATA:
        from app.services import mock_data
        notification = mock_data.MOCK_NOTIFICATIONS.get(notification_id)
        if not notification:
            raise HTTPException(status_code=404, detail="Notification not found.")
        notification.unread = False
        return notification

    notification = mongo_repo.mark_notification_read(get_db(), notification_id)
    if not notification:
        raise HTTPException(status_code=404, detail="Notification not found.")
    return notification