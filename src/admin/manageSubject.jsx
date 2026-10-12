import React, { useState, useEffect, useCallback, useMemo } from "react";

// Base URL of the Python backend — same as grade.jsx
const API_BASE = "http://localhost:8000";

// TEMPORARY placeholder auth header (see app/auth/dependencies.py on the backend).
const TEACHER_ID = "t1";

export default function ManageSubject() {
  const [subjects, setSubjects] = useState([]);
  const [assignments, setAssignments] = useState([]);
  const [activeTeacherCount, setActiveTeacherCount] = useState(0);
  const [sectionCoveredCount, setSectionCoveredCount] = useState(0);
  const [loading, setLoading] = useState(true);
  const [loadError, setLoadError] = useState(null);

  const [subjectCode, setSubjectCode] = useState("");
  const [subjectTitle, setSubjectTitle] = useState("");
  const [isAdding, setIsAdding] = useState(false);
  const [addError, setAddError] = useState(null);

  const fetchAll = useCallback(async () => {
    try {
      setLoading(true);
      setLoadError(null);

      const headers = { "x-teacher-id": TEACHER_ID };

      const [subjectsRes, assignmentsRes] = await Promise.all([
        fetch(`${API_BASE}/subjects`, { headers }),
        fetch(`${API_BASE}/assignments`, { headers }),
      ]);

      if (!subjectsRes.ok || !assignmentsRes.ok) {
        throw new Error("Failed to load subjects/assignments.");
      }

      const subjectsData = await subjectsRes.json();
      const assignmentsData = await assignmentsRes.json();

      setSubjects(subjectsData);
      setAssignments(assignmentsData);

      // "Active Teachers" / "Sections Covered" derived from assignment/schedules data
      const uniqueTeachers = new Set(assignmentsData.map((a) => a.teacher_id));
      const uniqueSections = new Set(assignmentsData.map((a) => a.section));
      setActiveTeacherCount(uniqueTeachers.size);
      setSectionCoveredCount(uniqueSections.size);
    } catch (err) {
      setLoadError(err.message);
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    fetchAll();
  }, [fetchAll]);

  // Dynamic Subjects List: Fallback to schedules/assignments data if /subjects collection is empty
  const displaySubjects = useMemo(() => {
    if (subjects && subjects.length > 0) {
      return subjects;
    }

    // Extract unique subjects from assignments/schedules collection
    const uniqueMap = new Map();
    assignments.forEach((item) => {
      if (item.subject_code && !uniqueMap.has(item.subject_code)) {
        uniqueMap.set(item.subject_code, {
          code: item.subject_code,
          title: item.subject_title || item.subject_code,
        });
      }
    });

    return Array.from(uniqueMap.values());
  }, [subjects, assignments]);

  const addSubject = async () => {
    if (!subjectCode.trim() || !subjectTitle.trim()) return;

    try {
      setIsAdding(true);
      setAddError(null);

      const response = await fetch(`${API_BASE}/subjects`, {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
          "x-teacher-id": TEACHER_ID,
        },
        body: JSON.stringify({
          code: subjectCode.trim().toUpperCase(),
          title: subjectTitle.trim(),
        }),
      });

      if (!response.ok) {
        const body = await response.json().catch(() => null);
        throw new Error(body?.detail || "Failed to add subject.");
      }

      setSubjectCode("");
      setSubjectTitle("");
      await fetchAll();
    } catch (err) {
      setAddError(err.message);
    } finally {
      setIsAdding(false);
    }
  };

  const deleteSubject = async (code) => {
    try {
      const response = await fetch(`${API_BASE}/subjects/${code}`, {
        method: "DELETE",
        headers: { "x-teacher-id": TEACHER_ID },
      });

      if (!response.ok) {
        throw new Error(`Failed to delete subject (status ${response.status})`);
      }

      await fetchAll();
    } catch (err) {
      setLoadError(err.message);
    }
  };

  return (
    <div className="h-full pl-[55%] md:pl-88 font-RB">
      <div className="p-10">
        {/* Header */}
        <div className="flex justify-between">
          <div className="font-medium">
            <h1 className="text-4xl">Manage Subjects</h1>
            <h1 className="text-xl text-black/50">
              Add or remove subjects available for teacher assignment.
            </h1>
          </div>

          <h1 className="font-medium text-[#996400]">ADMIN</h1>
        </div>

        {loadError && (
          <div className="mt-6 bg-red-50 border border-red-300 text-red-600 text-sm font-medium p-3 rounded-lg">
            {loadError}
          </div>
        )}

        {/* Statistics */}
        <div className="flex gap-15 mt-25 w-full">
          <div className="drop-shadow-lg/25 bg-white p-4 border border-[#4E3404]/50 w-79.25 rounded-xl">
            <h1 className="text-3xl font-medium">{displaySubjects.length}</h1>
            <h1 className="font-light">Active Subjects</h1>
          </div>

          <div className="drop-shadow-lg/25 bg-white p-4 border border-[#4E3404]/50 w-79.25 rounded-xl">
            <h1 className="text-3xl font-medium">{activeTeacherCount}</h1>
            <h1 className="font-light">Active Teachers</h1>
          </div>

          <div className="drop-shadow-lg/25 bg-white p-4 border border-[#4E3404]/50 w-79.25 rounded-xl">
            <h1 className="text-3xl font-medium">{sectionCoveredCount}</h1>
            <h1 className="font-light">Sections Covered</h1>
          </div>
        </div>

        {/* Subjects Container */}
        <div className="mt-10 bg-white border border-[#4E3404]/50 rounded-xl p-6 drop-shadow-lg/25">
          <h1 className="text-2xl font-semibold mb-6">Subjects</h1>

          {/* Subject List */}
          <div className="border-b overflow-hidden">
            {loading && (
              <div className="py-10 text-center text-gray-400">
                Loading...
              </div>
            )}

            {!loading && displaySubjects.length === 0 ? (
              <div className="py-10 text-center text-gray-400">
                No subjects added.
              </div>
            ) : (
              !loading &&
              displaySubjects.map((subject) => (
                <div
                  key={subject.code}
                  className="flex justify-between items-start px-5 py-4 border-b last:border-b-0"
                >
                  <div>
                    <div className="flex items-center gap-2">
                      <h1 className="font-medium text-xl">
                        {subject.code}
                      </h1>

                      <span className="text-[9px] uppercase px-2 py-1 rounded-full border border-[#0E5A12] bg-green-100 text-green-700">
                        Subject Code
                      </span>
                    </div>

                    <p className="text-gray-500 text-sm font-light">
                      {subject.title}
                    </p>
                  </div>

                  <button
                    onClick={() => deleteSubject(subject.code)}
                    className="w-7 h-7 flex items-center justify-center rounded border border-gray-300 text-gray-500 hover:bg-red-500 hover:text-white transition"
                    title="Delete subject"
                  >
                    ✕
                  </button>
                </div>
              ))
            )}
          </div>

          {/* Add Subject Input Form */}
          <div className="flex gap-3 mt-8">
            <input
              type="text"
              placeholder="Subject Code, e.g. CC101"
              value={subjectCode}
              onChange={(e) => setSubjectCode(e.target.value)}
              className="flex-1 border rounded-lg p-3 outline-none focus:ring-1 focus:ring-green-500"
            />

            <input
              type="text"
              placeholder="Subject Title, e.g. Introduction to Computing"
              value={subjectTitle}
              onChange={(e) => setSubjectTitle(e.target.value)}
              className="flex-2 border rounded-lg p-3 outline-none focus:ring-1 focus:ring-green-500"
            />

            <button
              onClick={addSubject}
              disabled={isAdding || !subjectCode.trim() || !subjectTitle.trim()}
              className="bg-[#3B8126] text-white px-8 rounded-lg active:scale-95 hover:bg-[#2d651d] transition disabled:opacity-50 disabled:cursor-not-allowed"
            >
              {isAdding ? "Adding..." : "Add Subject"}
            </button>
          </div>

          {addError && (
            <p className="text-sm text-red-600 mt-3">{addError}</p>
          )}
        </div>
      </div>
    </div>
  );
}