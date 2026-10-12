"""
Tests for app/services/mongo_repo.py using mongomock (an in-memory fake
MongoDB). Sample documents here match EXACTLY what was confirmed by
inspecting the real iiti_db collections in MongoDB Atlas.

These tests catch mapping/logic bugs (wrong field names, bad filtering,
broken deduplication) without needing a live MongoDB connection.
"""

import mongomock
import pytest
from datetime import datetime, timezone

from app.services import mongo_repo
from app.models.grade import GradeInput


@pytest.fixture
def db():
    client = mongomock.MongoClient()
    database = client["iiti_db"]

    prof_id = database.professors.insert_one({
        "name": "Casuco, Florentino S.",
        "sex": "male",
        "status": ["full-time", "part-time"],
        "remarks": "PT-FT",
        "position": "program director",
        "specializations": ["PF101", "MEI", "CC101", "CC104", "PT101"],
    }).inserted_id

    database.students.insert_many([
        {
            "studentNumber": "202310536", "firstName": "Kenneth", "lastName": "Tabuzo",
            "section": "A", "year": "1", "schoolYear": "2026-2027", "semester": "1st",
        },
        {
            "studentNumber": "202310537", "firstName": "Maria", "lastName": "Santos",
            "section": "A", "year": "1", "schoolYear": "2026-2027", "semester": "1st",
        },
        {
            # Different section — must NOT appear in BSIT-1A roster
            "studentNumber": "202310999", "firstName": "Wrong", "lastName": "Section",
            "section": "B", "year": "1", "schoolYear": "2026-2027",
        },
    ])

    database.schedules.insert_one({
        "curriculum_id": "master_schedule_AY2425_S1",
        "academic_year": "2024-2025",
        "semester": 2,
        "status": "Draft",
        "classes": [
            {
                "sectionName": "BSIT-1A", "subjectCode": "CC101", "day": "Monday",
                "startTime": 420, "endTime": 600, "roomId": "room2", "roomName": "Lab 1",
                "profId": str(prof_id), "profName": "Casuco, Florentino S.",
            },
            {
                # Same section+subject, different day — should be deduplicated
                "sectionName": "BSIT-1A", "subjectCode": "CC101", "day": "Wednesday",
                "startTime": 420, "endTime": 600, "roomId": "room2", "roomName": "Lab 1",
                "profId": str(prof_id), "profName": "Casuco, Florentino S.",
            },
            {
                # Different teacher — should NOT appear for prof_id above
                "sectionName": "BSIT-2B", "subjectCode": "SIA101", "day": "Tuesday",
                "startTime": 480, "endTime": 600, "roomId": "room3", "roomName": "Room 3",
                "profId": "some_other_prof_id", "profName": "Other Teacher",
            },
        ],
        "generated_at": datetime.now(timezone.utc),
    })

    database._test_prof_id = str(prof_id)
    return database


def test_list_teachers(db):
    teachers = mongo_repo.list_teachers(db)
    assert len(teachers) == 1
    assert teachers[0].full_name == "Casuco, Florentino S."


def test_get_teacher_by_id(db):
    teacher = mongo_repo.get_teacher_by_id(db, db._test_prof_id)
    assert teacher is not None
    assert teacher.full_name == "Casuco, Florentino S."


def test_get_teacher_by_invalid_id_returns_none(db):
    assert mongo_repo.get_teacher_by_id(db, "not-a-valid-objectid") is None


def test_parse_section_name():
    assert mongo_repo.parse_section_name("BSIT-1A") == ("1", "A")
    assert mongo_repo.parse_section_name("BSIT-3G") == ("3", "G")


def test_parse_section_name_rejects_bad_format():
    with pytest.raises(ValueError):
        mongo_repo.parse_section_name("not-a-section")


def test_list_sections_for_teacher_deduplicates_and_filters(db):
    sections = mongo_repo.list_sections_for_teacher(db, db._test_prof_id)
    # Monday + Wednesday classes for the same section+subject must collapse to one
    assert len(sections) == 1
    assert sections[0].subject_code == "CC101"
    assert "BSIT-1A" in sections[0].section


def test_list_sections_for_teacher_excludes_other_teachers(db):
    sections = mongo_repo.list_sections_for_teacher(db, "some_other_prof_id")
    assert len(sections) == 1
    assert sections[0].subject_code == "SIA101"


def test_list_students_in_section_filters_correctly(db):
    students = mongo_repo.list_students_in_section(db, "BSIT-1A")
    ids = {s.id for s in students}
    assert ids == {"202310536", "202310537"}
    assert "202310999" not in ids  # different section, must be excluded


def test_save_and_get_grades_round_trip(db):
    section_id = mongo_repo.make_section_id("BSIT-1A", "CC101")
    mongo_repo.save_grades_for_section(db, section_id, {
        "202310536": GradeInput(prelim=85, rawMid=88, rawPre=90, rawFinal=87)
    })

    grades = mongo_repo.get_grades_for_section(db, section_id)
    assert grades["202310536"].prelim == 85
    assert grades["202310536"].rawFinal == 87


def test_save_grades_upserts_not_duplicates(db):
    section_id = mongo_repo.make_section_id("BSIT-1A", "CC101")
    mongo_repo.save_grades_for_section(db, section_id, {
        "202310536": GradeInput(prelim=85)
    })
    mongo_repo.save_grades_for_section(db, section_id, {
        "202310536": GradeInput(prelim=90)  # update the same student again
    })

    count = db.grades.count_documents({"section_id": section_id, "student_id": "202310536"})
    assert count == 1  # must have updated in place, not inserted a second doc

    grades = mongo_repo.get_grades_for_section(db, section_id)
    assert grades["202310536"].prelim == 90


def test_get_section_by_id_reverse_lookup(db):
    section_id = mongo_repo.make_section_id("BSIT-1A", "CC101")
    result = mongo_repo.get_section_by_id(db, section_id)
    assert result == ("BSIT-1A", "CC101")


def test_get_section_by_id_not_found_returns_none(db):
    assert mongo_repo.get_section_by_id(db, "nonexistent-section") is None