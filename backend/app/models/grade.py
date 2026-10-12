from pydantic import BaseModel, Field
from typing import Optional


class Student(BaseModel):
    id: str
    name: str


class GradeInput(BaseModel):
    prelim: Optional[float] = Field(default=None, ge=0, le=100)
    rawMid: Optional[float] = Field(default=None, ge=0, le=100)
    rawPre: Optional[float] = Field(default=None, ge=0, le=100)
    rawFinal: Optional[float] = Field(default=None, ge=0, le=100)


class StudentGradeRow(BaseModel):
    id: str
    name: str
    prelim: Optional[float] = None
    rawMid: Optional[float] = None
    midterm: Optional[float] = None
    rawPre: Optional[float] = None
    prefinal: Optional[float] = None
    rawFinal: Optional[float] = None
    final: Optional[float] = None


class Section(BaseModel):
    id: str
    section: str
    subject_code: str
    subject_title: str
    academic_year: Optional[str] = None
    semester: Optional[str] = None


class Term(BaseModel):
    academic_year: str
    semester: str
    label: str


class SaveGradesRequest(BaseModel):
    grades: dict[str, GradeInput]


class Teacher(BaseModel):
    id: str
    full_name: str


class TeacherCreate(BaseModel):
    full_name: str


class TeacherAccountCreate(BaseModel):
    professor_id: str
    email: str = Field(min_length=3, max_length=254)
    password: str = Field(min_length=8, max_length=72)


class TeacherAccount(BaseModel):
    id: str
    professor_id: str
    username: str
    email: str
    institute: str
    role: str


class Subject(BaseModel):
    code: str
    title: str


class SubjectCreate(BaseModel):
    code: str
    title: str


class Assignment(BaseModel):
    id: str
    teacher_id: str
    teacher_name: str
    subject_code: str
    subject_title: str
    section: str


class AssignmentCreate(BaseModel):
    teacher_id: str
    subject_code: str
    section: str


class NotificationItem(BaseModel):
    id: str
    message: str
    time: str
    unread: bool


class NotificationCreate(BaseModel):
    message: str


class Deadline(BaseModel):
    term: str
    deadline_date: Optional[str] = None


class DeadlineSet(BaseModel):
    term: str
    deadline_date: str


class SendReminderRequest(BaseModel):
    term: str


class ReminderLogEntry(BaseModel):
    id: str
    term: str
    teacher_count: int
    sent_at: str
    status: str


# --- Term-based component grading (v2) ---
# Kept separate from the original flat GradeInput/StudentGradeRow (v1),
# which the live grade.jsx still uses. This avoids touching anything
# already working in production.

class GradeComponent(BaseModel):
    id: str
    label: str
    percentage: float


class GradeComponentCreate(BaseModel):
    label: str
    percentage: float = Field(ge=0, le=100)


class GradeComponentUpdate(BaseModel):
    label: Optional[str] = None
    percentage: Optional[float] = Field(default=None, ge=0, le=100)


class TermComponents(BaseModel):
    # Dynamic: keyed by grade component id (e.g. the id of "Quiz", "Exam",
    # or whatever admin-defined components currently exist), not fixed
    # named fields. This lets admins add/remove components freely.
    values: dict[str, float] = Field(default_factory=dict)


class SaveTermGradesRequest(BaseModel):
    term: str  # "prelim" | "midterm" | "prefinal" | "final"
    components: dict[str, TermComponents]  # keyed by student id


class StudentTermGradeRow(BaseModel):
    id: str
    name: str

    # Raw component inputs per term, so the per-term view can pre-fill
    # inputs when reopening a term that already has saved data.
    prelimComponents: TermComponents = TermComponents()
    midtermComponents: TermComponents = TermComponents()
    prefinalComponents: TermComponents = TermComponents()
    finalComponents: TermComponents = TermComponents()

    # Computed cascade (Overall view)
    prelim: Optional[float] = None
    midterm: Optional[float] = None
    prefinal: Optional[float] = None
    final: Optional[float] = None
    equivalent: Optional[float] = None


# --- Admin "View Grade" page (read-only) ---
# Same cascade as StudentTermGradeRow's Overall view, but also carries
# the raw per-term values (Raw Midterm / Raw Pre-Final / Raw Final),
# which the admin mockup shows but StudentTermGradeRow does not expose.

class ViewGradeRow(BaseModel):
    id: str
    name: str
    section: Optional[str] = None
    prelim: Optional[float] = None
    raw_midterm: Optional[float] = None
    midterm: Optional[float] = None
    raw_prefinal: Optional[float] = None
    prefinal: Optional[float] = None
    raw_final: Optional[float] = None
    final: Optional[float] = None
    equivalent: Optional[float] = None


class ViewGradeFilterOptions(BaseModel):
    courses: list[str]
    year_levels: list[str]
    sections: list[str]
    subjects: list[Subject]
    terms: list[Term]