import re
import bcrypt
from datetime import datetime, timezone
from bson import ObjectId
from bson.errors import InvalidId
from pymongo import ReturnDocument

from app.models.grade import Student, Section, Teacher, TeacherAccount, Subject, NotificationItem, Deadline, ReminderLogEntry, TermComponents, GradeComponent, Term
from app.services.grading import compute_term_raw, get_grade_equivalent

ALL_TERMS = ("prelim", "midterm", "prefinal", "final")

TEACHER_ROLE = "Teacher"
TEACHER_INSTITUTE = "IITI"  # TODO: take from the logged-in admin once real auth exists
BCRYPT_ROUNDS = 12  # matches the existing $2b$12$ hashes in users


TERMS = ["Prelim", "Midterm", "Pre-Final", "Final"]

SECTION_NAME_PATTERN = re.compile(r"^BSIT-(\d+)([A-Za-z]+)$")


def parse_section_name(section_name: str) -> tuple[str, str]:
    match = SECTION_NAME_PATTERN.match(section_name.strip())
    if not match:
        raise ValueError(
            f"Section name '{section_name}' doesn't match the expected "
            f"'BSIT-{{year}}{{letter}}' pattern (e.g. 'BSIT-1A')."
        )
    year, letter = match.groups()
    return year, letter


def make_section_id(section_name: str, subject_code: str, academic_year: str, semester: str) -> str:
    """Includes the academic year + semester so the same section/subject
    combo in a different term (e.g. BSIT-1A CC101 next school year) gets a
    distinct id instead of colliding with this term's data."""
    raw = f"{section_name}-{subject_code}-{academic_year}-{semester}"
    return raw.lower().replace(" ", "")


def list_teachers(db) -> list[Teacher]:
    docs = db.professors.find()
    return [Teacher(id=str(doc["_id"]), full_name=doc["name"]) for doc in docs]


def get_teacher_by_id(db, teacher_id: str) -> Teacher | None:
    try:
        oid = ObjectId(teacher_id)
    except InvalidId:
        return None
    doc = db.professors.find_one({"_id": oid})
    if not doc:
        return None
    return Teacher(id=str(doc["_id"]), full_name=doc["name"])


# --- Teacher accounts (logins in the shared `users` collection) ---
# Same document shape as the existing Admin accounts so other systems can
# log these teachers in too. `professorId` links the account to the
# professors collection (same value as `profId` in schedules.classes).
# professors itself is never written to.

def _to_teacher_account(doc: dict) -> TeacherAccount:
    return TeacherAccount(
        id=str(doc["_id"]),
        professor_id=doc.get("professorId", ""),
        username=doc.get("username", ""),
        email=doc.get("email", ""),
        institute=doc.get("institute", ""),
        role=doc.get("role", ""),
    )


def list_teacher_accounts(db) -> list[TeacherAccount]:
    docs = db.users.find({"role": TEACHER_ROLE})
    return [_to_teacher_account(doc) for doc in docs]


def create_teacher_account(db, professor_id: str, email: str, password: str) -> TeacherAccount:
    professor = get_teacher_by_id(db, professor_id)
    if not professor:
        raise LookupError("Professor not found.")

    email_clean = email.strip().lower()
    if db.users.find_one({"email": {"$regex": f"^{re.escape(email_clean)}$", "$options": "i"}}):
        raise ValueError("An account with this email already exists.")
    if db.users.find_one({"professorId": professor_id, "role": TEACHER_ROLE}):
        raise ValueError("This professor already has an account.")

    password_bytes = password.encode("utf-8")
    if len(password_bytes) > 72:
        raise ValueError("Password is too long (max 72 bytes).")
    hashed = bcrypt.hashpw(password_bytes, bcrypt.gensalt(rounds=BCRYPT_ROUNDS)).decode("utf-8")

    doc = {
        "username": professor.full_name,
        "email": email_clean,
        "password": hashed,
        "institute": TEACHER_INSTITUTE,
        "role": TEACHER_ROLE,
        "professorId": professor_id,
    }
    inserted = db.users.insert_one(doc)
    doc["_id"] = inserted.inserted_id
    return _to_teacher_account(doc)


def list_subjects(db) -> list[Subject]:
    docs = db.subjects.find()
    return [Subject(code=doc["code"], title=doc["title"]) for doc in docs]


def get_subject_title(db, subject_code: str) -> str:
    doc = db.subjects.find_one({"code": subject_code})
    return doc["title"] if doc else subject_code


def add_subject(db, code: str, title: str) -> Subject:
    if db.subjects.find_one({"code": code}):
        raise ValueError(f"Subject '{code}' already exists.")
    db.subjects.insert_one({"code": code, "title": title})
    return Subject(code=code, title=title)


def delete_subject(db, code: str) -> bool:
    result = db.subjects.delete_one({"code": code})
    return result.deleted_count > 0


def _get_all_classes(db) -> list[dict]:
    """
    There isn't just one 'the' schedule document — there can be multiple
    (one per program/year/section/term combination). We need to search
    across ALL of them, not just the most recent one.

    Each schedule document carries `academicYear` and `semester` at the
    TOP level, not inside each class entry — so we copy those two fields
    down into every flattened class dict here, once, so every caller down
    the line can tell which term a class belongs to without having to
    know about the parent schedule document at all.
    """
    all_classes = []
    for schedule in db.schedules.find():
        academic_year = schedule.get("academicYear")
        semester = schedule.get("semester")
        for cls in schedule.get("classes", []):
            cls_with_term = dict(cls)
            cls_with_term["academicYear"] = academic_year
            cls_with_term["semester"] = semester
            all_classes.append(cls_with_term)
    return all_classes


def list_available_terms(db) -> list[Term]:
    """Distinct academic year + semester pairs found across all schedules,
    sorted latest first (highest starting year, then '2nd' before '1st')."""
    seen = set()
    for schedule in db.schedules.find():
        academic_year = schedule.get("academicYear")
        semester = schedule.get("semester")
        if academic_year and semester:
            seen.add((academic_year, semester))

    def sort_key(pair: tuple[str, str]):
        year, sem = pair
        try:
            start_year = int(year.split("-")[0])
        except (ValueError, IndexError):
            start_year = 0
        sem_rank = 2 if sem.strip().lower().startswith("2") else 1
        return (start_year, sem_rank)

    ordered = sorted(seen, key=sort_key, reverse=True)
    return [
        Term(academic_year=year, semester=sem, label=f"{sem} Semester, AY {year}")
        for year, sem in ordered
    ]


def is_term_current(db, academic_year: str, semester: str) -> bool:
    """A term is "current" if it is the most recent academic year +
    semester found in schedules.classes — the one teachers should still
    be actively grading. Any earlier term is finished and locked against
    further teacher edits once a newer term exists. If no terms exist yet
    at all, nothing is locked (there's nothing to compare against)."""
    terms = list_available_terms(db)
    if not terms:
        return True
    latest = terms[0]
    return latest.academic_year == academic_year and latest.semester == semester


def list_sections_for_teacher(
    db, teacher_id: str, academic_year: str | None = None, semester: str | None = None
) -> list[Section]:
    seen: dict[str, Section] = {}
    for cls in _get_all_classes(db):
        if cls.get("profId") != teacher_id:
            continue

        cls_year = cls.get("academicYear")
        cls_sem = cls.get("semester")
        if academic_year and cls_year != academic_year:
            continue
        if semester and cls_sem != semester:
            continue

        section_name = cls["sectionName"]
        subject_code = cls["subjectCode"]
        section_id = make_section_id(section_name, subject_code, cls_year, cls_sem)
        if section_id not in seen:
            seen[section_id] = Section(
                id=section_id,
                section=f"{section_name} - {subject_code} - {get_subject_title(db, subject_code)}",
                subject_code=subject_code,
                subject_title=get_subject_title(db, subject_code),
                academic_year=cls_year,
                semester=cls_sem,
            )
    return list(seen.values())


def list_all_assignments(db):
    """
    Read-only view of every teacher-subject-section pairing, derived
    directly from the latest schedules.classes — this IS the real
    'assignments' data, already owned by the schedules system. No
    separate collection needed; we just present it in the Assignment shape
    the admin UI expects.
    """
    from app.models.grade import Assignment

    seen: dict[str, Assignment] = {}
    for cls in _get_all_classes(db):
        prof_id = cls.get("profId")
        section_name = cls.get("sectionName")
        subject_code = cls.get("subjectCode")
        if not prof_id or not section_name or not subject_code:
            continue

        key = f"{prof_id}-{section_name}-{subject_code}"
        if key not in seen:
            seen[key] = Assignment(
                id=key,
                teacher_id=prof_id,
                teacher_name=cls.get("profName", ""),
                subject_code=subject_code,
                subject_title=get_subject_title(db, subject_code),
                section=section_name,
            )

    return list(seen.values())


def get_section_by_id(db, section_id: str) -> tuple[str, str, str, str] | None:
    """Returns (section_name, subject_code, academic_year, semester)."""
    for cls in _get_all_classes(db):
        section_name = cls["sectionName"]
        subject_code = cls["subjectCode"]
        academic_year = cls.get("academicYear")
        semester = cls.get("semester")
        if make_section_id(section_name, subject_code, academic_year, semester) == section_id:
            return section_name, subject_code, academic_year, semester
    return None


def list_students_in_section(db, section_name: str) -> list[Student]:
    year, letter = parse_section_name(section_name)
    docs = db.students.find({"year": year, "section": letter})
    students = []
    for doc in docs:
        full_name = " ".join(part for part in [doc.get("firstName"), doc.get("lastName")] if part)
        students.append(Student(id=doc["studentNumber"], name=full_name))
    return students


def _format_full_name(doc: dict) -> str:
    """'Last, First M. Suffix' formatting, used by the admin View Grade
    page. Kept separate from list_students_in_section's 'First Last'
    format so the live Grade page's display is untouched."""
    last = doc.get("lastName", "")
    first = doc.get("firstName", "")
    middle = doc.get("middleName", "")
    suffix = doc.get("suffix", "")
    name = f"{last}, {first}"
    if middle:
        name += f" {middle[0]}."
    if suffix:
        name += f" {suffix}"
    return name


def list_students_in_section_view(db, section_name: str) -> list[Student]:
    """Same section lookup as list_students_in_section, but returns
    'Last, First M.' formatted names for the admin View Grade page."""
    year, letter = parse_section_name(section_name)
    docs = db.students.find({"year": year, "section": letter})
    return [Student(id=doc["studentNumber"], name=_format_full_name(doc)) for doc in docs]


def list_view_grade_filter_options(
    db,
    year_level: str | None = None,
    section: str | None = None,
    academic_year: str | None = None,
    semester: str | None = None,
) -> dict:
    """Builds the options for the View Grade page's dropdowns. Year Level
    and Section are scoped to the given term (if provided). Subject is
    further scoped down to only what's taught to the given
    year_level + section within that term, if both are provided."""
    year_letters = set()
    subject_codes = set()

    for cls in _get_all_classes(db):
        if academic_year and cls.get("academicYear") != academic_year:
            continue
        if semester and cls.get("semester") != semester:
            continue

        try:
            year, letter = parse_section_name(cls["sectionName"])
        except ValueError:
            continue

        year_letters.add((year, letter))

        if year_level and section:
            if year != year_level or letter != section:
                continue

        subject_code = cls.get("subjectCode")
        if subject_code:
            subject_codes.add(subject_code)

    subjects = [Subject(code=code, title=get_subject_title(db, code)) for code in sorted(subject_codes)]

    return {
        "courses": ["BSIT"],
        "year_levels": sorted({y for y, _ in year_letters}),
        "sections": sorted({l for _, l in year_letters}),
        "subjects": subjects,
        "terms": list_available_terms(db),
    }


def find_students_by_subject_and_query(
    db, subject_code: str, academic_year: str, semester: str, query: str
) -> list[tuple[Student, str]]:
    """
    Case-insensitive search for students taking `subject_code` IN THE GIVEN
    TERM, matched by name or student number, across every section that
    teaches it that term. Returns (Student, section_name) pairs since the
    caller needs the section to look up that student's grades data.
    """
    query_lower = query.strip().lower()
    if not query_lower:
        return []

    seen_sections = set()
    matches: list[tuple[Student, str]] = []

    for cls in _get_all_classes(db):
        if cls.get("subjectCode") != subject_code:
            continue
        if cls.get("academicYear") != academic_year or cls.get("semester") != semester:
            continue

        section_name = cls.get("sectionName")
        if not section_name or section_name in seen_sections:
            continue
        seen_sections.add(section_name)

        try:
            students = list_students_in_section_view(db, section_name)
        except ValueError:
            continue

        for student in students:
            if query_lower in student.name.lower() or query_lower in student.id.lower():
                matches.append((student, section_name))

    return matches


# --- Notifications (new collection: grading_notifications) ---
# Deliberately NOT reusing the existing `notifications` collection — that
# one belongs to the enrollment system and has its own schema/purpose.
# Mixing grading reminders into it risks breaking their system's
# assumptions about what's in there. This is our own, separate collection.

def list_notifications(db) -> list[NotificationItem]:
    docs = db.grading_notifications.find().sort("created_at", -1)
    return [
        NotificationItem(
            id=str(doc["_id"]),
            message=doc["message"],
            time=doc["time"],
            unread=doc["unread"],
        )
        for doc in docs
    ]


def mark_notification_read(db, notification_id: str) -> NotificationItem | None:
    try:
        oid = ObjectId(notification_id)
    except InvalidId:
        return None

    result = db.grading_notifications.find_one_and_update(
        {"_id": oid},
        {"$set": {"unread": False}},
        return_document=ReturnDocument.AFTER,
    )
    if not result:
        return None
    return NotificationItem(
        id=str(result["_id"]), message=result["message"],
        time=result["time"], unread=result["unread"],
    )


def add_notification(db, message: str, time_str: str) -> NotificationItem:
    doc = {
        "message": message,
        "time": time_str,
        "unread": True,
        "created_at": datetime.now(timezone.utc),
    }
    inserted = db.grading_notifications.insert_one(doc)
    return NotificationItem(id=str(inserted.inserted_id), message=message, time=time_str, unread=True)


# --- Deadlines & Reminders (new collections: grading_deadlines, grading_reminder_log) ---
# `systemsettings` in iiti_db is occupied by another team's data, so these
# get their own dedicated collections, same reasoning as grading_notifications.

def get_active_teacher_count(db) -> int:
    """Counts unique professors who have at least one class across all
    schedules — used as the 'teacher_count' when sending a real reminder."""
    return len({cls.get("profId") for cls in _get_all_classes(db) if cls.get("profId")})


def list_deadlines(db) -> list[Deadline]:
    saved = {doc["term"]: doc.get("deadline_date") for doc in db.grading_deadlines.find()}
    return [Deadline(term=term, deadline_date=saved.get(term)) for term in TERMS]


def set_deadline(db, term: str, deadline_date: str) -> Deadline:
    db.grading_deadlines.update_one(
        {"term": term},
        {"$set": {"deadline_date": deadline_date, "updated_at": datetime.now(timezone.utc)}},
        upsert=True,
    )
    return Deadline(term=term, deadline_date=deadline_date)


def list_reminder_log(db) -> list[ReminderLogEntry]:
    docs = db.grading_reminder_log.find().sort("created_at", -1)
    return [
        ReminderLogEntry(
            id=str(doc["_id"]), term=doc["term"], teacher_count=doc["teacher_count"],
            sent_at=doc["sent_at"], status=doc["status"],
        )
        for doc in docs
    ]


def add_reminder_log_entry(db, term: str, teacher_count: int, sent_at: str) -> ReminderLogEntry:
    doc = {
        "term": term, "teacher_count": teacher_count, "sent_at": sent_at,
        "status": "SENT", "created_at": datetime.now(timezone.utc),
    }
    inserted = db.grading_reminder_log.insert_one(doc)
    return ReminderLogEntry(id=str(inserted.inserted_id), term=term, teacher_count=teacher_count, sent_at=sent_at, status="SENT")


def get_term_data_for_section(
    db, section_name: str, subject_code: str, academic_year: str, semester: str
) -> dict[str, dict[str, TermComponents]]:
    """Returns { student_id: { "prelim": TermComponents, "midterm": ..., ... } }
    scoped to one specific academic year + semester, so grades from a
    different term with the same section/subject never mix together."""
    docs = db.grades.find({
        "section": section_name,
        "subject_code": subject_code,
        "academic_year": academic_year,
        "semester": semester,
    })
    result = {}
    for doc in docs:
        student_terms = {}
        for term in ("prelim", "midterm", "prefinal", "final"):
            term_doc = doc.get(term)
            if term_doc:
                student_terms[term] = TermComponents(**term_doc)
        result[doc["student_id"]] = student_terms
    return result


def save_term_components(
    db,
    section_name: str,
    subject_code: str,
    academic_year: str,
    semester: str,
    term: str,
    components: dict[str, TermComponents],
) -> None:
    """Upserts the given term's components for each student, then freezes
    that one term's raw value onto the document under `rawSnapshots.<term>`,
    computed from whatever grade components are configured RIGHT NOW. This
    snapshot is permanent — it is only ever overwritten by explicitly
    re-saving that same term again later, never touched by saving a
    different term.

    The full cascade (Prelim -> Final -> Equivalent) is then rebuilt purely
    from whatever raw snapshots already exist for this student (frozen
    values, not recomputed from current components) and stored under
    `computedGrades`. This is what keeps editing Midterm from silently
    altering an already-graded Prelim, and what keeps a graduated
    student's historical grades stable even if the admin later changes or
    deletes a grade component — only re-saving that specific term can
    change its frozen raw value.

    `computedGrades` is also what other systems reading iiti_db directly
    (outside this API) should read for the official final numbers, rather
    than recomputing the 30/70 formula themselves from the raw per-term
    scores."""
    grade_components = list_grade_components(db)
    raw_value_for_this_term = None  # computed once per student below

    for student_id, term_components in components.items():
        key = {
            "section": section_name,
            "subject_code": subject_code,
            "academic_year": academic_year,
            "semester": semester,
            "student_id": student_id,
        }

        raw_value_for_this_term = compute_term_raw(term_components, grade_components)

        db.grades.update_one(
            key,
            {"$set": {
                term: term_components.model_dump(),
                f"rawSnapshots.{term}": raw_value_for_this_term,
                "updated_at": datetime.now(timezone.utc),
            }},
            upsert=True,
        )

        doc = db.grades.find_one(key)
        raw_snapshots = doc.get("rawSnapshots", {})

        raw_prelim = raw_snapshots.get("prelim")
        raw_mid = raw_snapshots.get("midterm")
        raw_pre = raw_snapshots.get("prefinal")
        raw_final = raw_snapshots.get("final")

        prelim = raw_prelim
        midterm = round((prelim * 0.30) + (raw_mid * 0.70), 2) if prelim is not None and raw_mid is not None else None
        prefinal = round((midterm * 0.30) + (raw_pre * 0.70), 2) if midterm is not None and raw_pre is not None else None
        final = round((prefinal * 0.30) + (raw_final * 0.70), 2) if prefinal is not None and raw_final is not None else None
        equivalent = get_grade_equivalent(final)

        db.grades.update_one(
            key,
            {"$set": {
                "computedGrades": {
                    "prelim": prelim,
                    "raw_midterm": raw_mid,
                    "midterm": midterm,
                    "raw_prefinal": raw_pre,
                    "prefinal": prefinal,
                    "raw_final": raw_final,
                    "final": final,
                    "equivalent": equivalent,
                },
            }},
        )


def get_full_grades_for_section(
    db, section_name: str, subject_code: str, academic_year: str, semester: str
) -> dict[str, dict]:
    """Returns { student_id: { "components": {term: TermComponents, ...},
    "computed": {prelim, raw_midterm, midterm, ...} } } for one term,
    reading the frozen `computedGrades` snapshot directly rather than
    recomputing anything — see save_term_components for why that matters."""
    docs = db.grades.find({
        "section": section_name,
        "subject_code": subject_code,
        "academic_year": academic_year,
        "semester": semester,
    })
    result = {}
    for doc in docs:
        term_components = {}
        for t in ALL_TERMS:
            term_doc = doc.get(t)
            if term_doc:
                term_components[t] = TermComponents(**term_doc)
        result[doc["student_id"]] = {
            "components": term_components,
            "computed": doc.get("computedGrades") or {},
        }
    return result


def list_grade_components(db) -> list[GradeComponent]:
    docs = db.grading_components.find().sort("_order", 1)
    return [GradeComponent(id=str(doc["_id"]), label=doc["label"], percentage=doc["percentage"]) for doc in docs]


def add_grade_component(db, label: str, percentage: float) -> GradeComponent:
    max_order_doc = db.grading_components.find_one(sort=[("_order", -1)])
    next_order = (max_order_doc["_order"] + 1) if max_order_doc else 0
    result = db.grading_components.insert_one({"label": label, "percentage": percentage, "_order": next_order})
    return GradeComponent(id=str(result.inserted_id), label=label, percentage=percentage)


def update_grade_component(db, component_id: str, label: str | None, percentage: float | None) -> GradeComponent | None:
    try:
        oid = ObjectId(component_id)
    except InvalidId:
        return None

    updates = {}
    if label is not None:
        updates["label"] = label
    if percentage is not None:
        updates["percentage"] = percentage
    if not updates:
        doc = db.grading_components.find_one({"_id": oid})
    else:
        doc = db.grading_components.find_one_and_update({"_id": oid}, {"$set": updates}, return_document=ReturnDocument.AFTER)

    if not doc:
        return None
    return GradeComponent(id=str(doc["_id"]), label=doc["label"], percentage=doc["percentage"])


def delete_grade_component(db, component_id: str) -> bool:
    try:
        oid = ObjectId(component_id)
    except InvalidId:
        return False

    result = db.grading_components.delete_one({"_id": oid})
    return result.deleted_count > 0