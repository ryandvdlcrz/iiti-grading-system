from app.models.grade import (
    Student, Section, GradeInput, Teacher, Subject, Assignment,
    NotificationItem, Deadline, ReminderLogEntry, TeacherAccount,
)

MOCK_SECTIONS: dict[str, Section] = {
    "cc101-bsit1a": Section(id="cc101-bsit1a", section="BSIT 1A - CC101 - Introduction to Computing", subject_code="CC101", subject_title="Introduction to Computing"),
    "cc101-bsit1b": Section(id="cc101-bsit1b", section="BSIT 1B - CC101 - Introduction to Computing", subject_code="CC101", subject_title="Introduction to Computing"),
    "cc101-bsit1c": Section(id="cc101-bsit1c", section="BSIT 1C - CC101 - Introduction to Computing", subject_code="CC101", subject_title="Introduction to Computing"),
    "cc101-bsit1f": Section(id="cc101-bsit1f", section="BSIT 1F - CC101 - Introduction to Computing", subject_code="CC101", subject_title="Introduction to Computing"),
    "cc101-bsit1g": Section(id="cc101-bsit1g", section="BSIT 1G - CC101 - Introduction to Computing", subject_code="CC101", subject_title="Introduction to Computing"),
}

MOCK_STUDENTS: dict[str, list[Student]] = {
    "cc101-bsit1a": [Student(id="202410001", name="Juan Dela Cruz"), Student(id="202410002", name="Maria Santos"), Student(id="202410003", name="John Reyes"), Student(id="202410004", name="Angela Cruz"), Student(id="202410005", name="Mark Bautista")],
    "cc101-bsit1b": [Student(id="20210006", name="Richard Grayson"), Student(id="20210007", name="Abegail Ramos"), Student(id="20210008", name="Christian Garcia"), Student(id="20210009", name="Ryan Dela Cruz"), Student(id="20210010", name="Gerwin Ni\u00f1o")],
    "cc101-bsit1c": [Student(id="20210011", name="Nicole Perez"), Student(id="20210012", name="Joshua Lim"), Student(id="20210013", name="Patricia Flores"), Student(id="20210014", name="Kevin Mendoza"), Student(id="20210015", name="Sophia Ramos")],
    "cc101-bsit1f": [Student(id="202410016", name="Ethan Villanueva"), Student(id="202410017", name="Daniel Gomez"), Student(id="202410018", name="Kimberly Torres"), Student(id="202410019", name="Aaron Cruz"), Student(id="202410020", name="Jasmine Rivera")],
    "cc101-bsit1g": [Student(id="202410021", name="Nathan Reyes"), Student(id="202410022", name="Isabella Lopez"), Student(id="202410023", name="Matthew Santos"), Student(id="202410024", name="Chloe Garcia"), Student(id="202410025", name="Miguel Hernandez")],
}

MOCK_GRADES_STORE: dict[str, dict[str, GradeInput]] = {section_id: {} for section_id in MOCK_SECTIONS}

MOCK_TEACHERS: dict[str, Teacher] = {
    "t1": Teacher(id="t1", full_name="Ms. Jamie Chico"),
    "t2": Teacher(id="t2", full_name="Mr. John Cruz"),
    "t3": Teacher(id="t3", full_name="Mrs. Reny Baterbonia"),
    "t4": Teacher(id="t4", full_name="Marvic Ablaza"),
}

MOCK_SUBJECTS: dict[str, Subject] = {
    "IPT102": Subject(code="IPT102", title="[ Subject Title ]"),
    "CC103": Subject(code="CC103", title="Programming 2"),
    "REN3": Subject(code="REN3", title="Life & Work of Rene"),
    "SIA101": Subject(code="SIA101", title="System Integration and Architecture 1"),
    "CC101": Subject(code="CC101", title="Introduction to Computing"),
}

MOCK_ASSIGNMENTS: dict[str, Assignment] = {
    "a1": Assignment(id="a1", teacher_id="t4", teacher_name="Marvic Ablaza", subject_code="SIA101", subject_title="System Integration and Architecture 1", section="BSIT 1B"),
}

_assignment_counter = {"n": 2}


def next_assignment_id() -> str:
    aid = f"a{_assignment_counter['n']}"
    _assignment_counter["n"] += 1
    return aid


_teacher_counter = {"n": 5}


def next_teacher_id() -> str:
    tid = f"t{_teacher_counter['n']}"
    _teacher_counter["n"] += 1
    return tid


MOCK_TEACHER_ACCOUNTS: dict[str, TeacherAccount] = {}

_teacher_account_counter = {"n": 1}


def next_teacher_account_id() -> str:
    aid = f"ta{_teacher_account_counter['n']}"
    _teacher_account_counter["n"] += 1
    return aid


MOCK_NOTIFICATIONS: dict[str, NotificationItem] = {
    "n1": NotificationItem(id="n1", message="Midterm grades are due soon \u2014 please submit by Jul 24.", time="Jul 12, 9:03 AM", unread=True),
    "n2": NotificationItem(id="n2", message="Prepare for The Second Coming of Rene.", time="Jul 10, 6:56 AM", unread=False),
}


# --- Deadlines & Reminders ---

TERMS = ["Prelim", "Midterm", "Pre-Final", "Final"]

MOCK_DEADLINES: dict[str, Deadline] = {
    term: Deadline(term=term, deadline_date=None) for term in TERMS
}

MOCK_REMINDER_LOG: list[ReminderLogEntry] = []

_reminder_counter = {"n": 1}


def next_reminder_id() -> str:
    rid = f"r{_reminder_counter['n']}"
    _reminder_counter["n"] += 1
    return rid


_notification_counter = {"n": 3}  # n1, n2 already used above


def next_notification_id() -> str:
    nid = f"n{_notification_counter['n']}"
    _notification_counter["n"] += 1
    return nid