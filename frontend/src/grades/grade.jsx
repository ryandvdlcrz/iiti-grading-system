import React, { useState, useEffect, useCallback, useRef } from "react";
import { MdWavingHand } from "react-icons/md";
import { FaSquare } from "react-icons/fa";
import { LuDownload } from "react-icons/lu";
import { FiUpload } from "react-icons/fi";

const API_BASE = "http://localhost:8000";
const TEACHER_ID = "6a71ae476300e08da083cd32";

// Raw term preview, computed from the admin-defined grade components
// (label + percentage) instead of hardcoded weights.
function computeTermRawPreview(values, gradeComponents) {
  if (!values || gradeComponents.length === 0) return null;
  let total = 0;
  for (const c of gradeComponents) {
    const v = values[c.id];
    if (v === "" || v === undefined || v === null) return null;
    total += Number(v) * (c.percentage / 100);
  }
  return Math.round(total * 100) / 100;
}

const TERMS = ["Prelim", "Midterm", "Pre-Final", "Final"];
const TERM_KEYS = { "Prelim": "prelim", "Midterm": "midterm", "Pre-Final": "prefinal", "Final": "final" };

// Reads the `.values` dictionary from the Pydantic TermComponents model.
// Keys are grade component ids.
function extractComponentsFromBackend(row, termKey) {
  if (!row) return {};
  const termObj = row[`${termKey}Components`] || {};
  return { ...(termObj.values || {}) };
}

// A school term (academic year + semester) is encoded as "year|semester"
// for use as a single <select> value, since the two always travel together.
function encodeTermKey(t) {
  return `${t.academic_year}|${t.semester}`;
}
function decodeTermKey(key) {
  const [academic_year, semester] = key.split("|");
  return { academic_year, semester };
}

function Grade() {
  const [teacherName, setTeacherName] = useState("");

  // School term (academic year + semester) — drives which sections/grades load
  const [academicTerms, setAcademicTerms] = useState([]);
  const [selectedAcademicTerm, setSelectedAcademicTerm] = useState(""); // "year|semester"
  const [academicTermsError, setAcademicTermsError] = useState(null);

  const [sections, setSections] = useState([]);
  const [selectedSectionId, setSelectedSectionId] = useState(null);
  const [sectionsLoading, setSectionsLoading] = useState(true);
  const [sectionsError, setSectionsError] = useState(null);

  const [gradeComponents, setGradeComponents] = useState([]);
  const [componentsError, setComponentsError] = useState(null);

  const [selectedTerm, setSelectedTerm] = useState("Midterm");

  const [rows, setRows] = useState([]);
  const [rowsLoading, setRowsLoading] = useState(false);
  const [rowsError, setRowsError] = useState(null);

  const [editedComponents, setEditedComponents] = useState({});
  const [isSaving, setIsSaving] = useState(false);
  const [saveMessage, setSaveMessage] = useState(null);

  const [isUploading, setIsUploading] = useState(false);
  const fileInputRef = useRef(null);

  useEffect(() => {
    async function fetchMe() {
      try {
        const response = await fetch(`${API_BASE}/me`, { headers: { "x-teacher-id": TEACHER_ID } });
        if (!response.ok) throw new Error("Failed to load teacher profile");
        const data = await response.json();
        setTeacherName(data.full_name);
      } catch (err) {
        setTeacherName("Teacher");
      }
    }
    fetchMe();
  }, []);

  // Available school terms, latest first (backend already sorts this way).
  // Defaults to the most recent term the moment it loads.
  useEffect(() => {
    async function fetchTerms() {
      try {
        setAcademicTermsError(null);
        const response = await fetch(`${API_BASE}/sections/terms`, {
          headers: { "x-teacher-id": TEACHER_ID },
        });
        if (!response.ok) throw new Error(`Failed to load terms (status ${response.status})`);
        const data = await response.json();
        setAcademicTerms(data);
        if (data.length > 0) setSelectedAcademicTerm(encodeTermKey(data[0]));
      } catch (err) {
        setAcademicTermsError(err.message);
      }
    }
    fetchTerms();
  }, []);

  // Sections for the currently selected school term. Refetches and resets
  // the chosen section whenever the term changes.
  useEffect(() => {
    if (!selectedAcademicTerm) return;

    async function fetchSections() {
      try {
        setSectionsLoading(true);
        setSectionsError(null);
        const { academic_year, semester } = decodeTermKey(selectedAcademicTerm);
        const params = new URLSearchParams({ academic_year, semester });
        const response = await fetch(`${API_BASE}/sections?${params.toString()}`, {
          headers: { "x-teacher-id": TEACHER_ID },
        });
        if (!response.ok) throw new Error(`Failed to load sections (status ${response.status})`);
        const data = await response.json();
        setSections(data);
        setSelectedSectionId(data.length > 0 ? data[0].id : null);
      } catch (err) {
        setSectionsError(err.message);
      } finally {
        setSectionsLoading(false);
      }
    }
    fetchSections();
  }, [selectedAcademicTerm]);

  // Grade components set by the admin on the Grade Components page
  useEffect(() => {
    async function fetchGradeComponents() {
      try {
        setComponentsError(null);
        const response = await fetch(`${API_BASE}/grade-components`, {
          headers: { "x-teacher-id": TEACHER_ID },
        });
        if (!response.ok) throw new Error(`Failed to load grade components (status ${response.status})`);
        setGradeComponents(await response.json());
      } catch (err) {
        setComponentsError(err.message);
      }
    }
    fetchGradeComponents();
  }, []);

  const seedComponents = useCallback((dataRows, term) => {
    if (term === "Overall") return;
    const termKey = TERM_KEYS[term];

    const seeded = {};
    dataRows.forEach((row) => {
      seeded[row.id] = extractComponentsFromBackend(row, termKey);
    });
    setEditedComponents(seeded);
  }, []);

  const fetchTermGrades = useCallback(async () => {
    if (!selectedSectionId) return;
    try {
      setRowsLoading(true);
      setRowsError(null);
      const response = await fetch(`${API_BASE}/sections/${selectedSectionId}/termgrades`, {
        headers: { "x-teacher-id": TEACHER_ID },
      });
      if (!response.ok) throw new Error(`Failed to load grades (status ${response.status})`);
      const data = await response.json();
      setRows(data);
      seedComponents(data, selectedTerm);
    } catch (err) {
      setRowsError(err.message);
      setRows([]);
    } finally {
      setRowsLoading(false);
    }
  }, [selectedSectionId, selectedTerm, seedComponents]);

  useEffect(() => {
    fetchTermGrades();
  }, [fetchTermGrades]);

  const handleTermChange = (newTerm) => {
    setSelectedTerm(newTerm);
    seedComponents(rows, newTerm);
  };

  const handleComponentChange = (studentId, field, rawValue) => {
    let val = rawValue;
    if (rawValue !== "") {
      const parsed = Number(rawValue);
      if (isNaN(parsed)) return;
      val = parsed > 100 ? 100 : parsed < 0 ? 0 : parsed;
    }

    setEditedComponents((prev) => ({
      ...prev,
      [studentId]: {
        ...prev[studentId],
        [field]: val,
      },
    }));
  };

  const getComponents = (studentId) => editedComponents[studentId] || {};

  // Saves scores keyed by grade component id, wrapped in `values`
  // to match SaveTermGradesRequest and TermComponents on the backend.
  const handleSaveGrades = async () => {
    if (!selectedSectionId || selectedTerm === "Overall" || gradeComponents.length === 0 || !isCurrentTerm) return;
    const termKey = TERM_KEYS[selectedTerm];

    const payloadComponents = {};
    rows.forEach((row) => {
      const c = getComponents(row.id);
      const valuesDict = {};
      gradeComponents.forEach((comp) => {
        const v = c[comp.id];
        if (v !== "" && v !== undefined && v !== null) valuesDict[comp.id] = Number(v);
      });
      payloadComponents[row.id] = { values: valuesDict };
    });

    try {
      setIsSaving(true);
      setSaveMessage(null);
      const response = await fetch(`${API_BASE}/sections/${selectedSectionId}/termgrades`, {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
          "x-teacher-id": TEACHER_ID,
        },
        body: JSON.stringify({
          term: termKey,
          components: payloadComponents,
        }),
      });

      if (!response.ok) {
        const body = await response.json().catch(() => null);
        throw new Error(body?.detail || "Failed to save grades.");
      }

      const updated = await response.json();
      setRows(updated);
      seedComponents(updated, selectedTerm);

      setSaveMessage({ type: "success", text: "Grades saved successfully!" });
    } catch (err) {
      setSaveMessage({ type: "error", text: err.message });
    } finally {
      setIsSaving(false);
      setTimeout(() => setSaveMessage(null), 4000);
    }
  };

  const handleDownloadCSV = async () => {
    if (!selectedSectionId || isOverall) return;
    const termKey = TERM_KEYS[selectedTerm];
    try {
      const response = await fetch(
        `${API_BASE}/sections/${selectedSectionId}/termgrades/csv?term=${termKey}`,
        { headers: { "x-teacher-id": TEACHER_ID } }
      );
      if (!response.ok) throw new Error("Download failed.");

      const disposition = response.headers.get("Content-Disposition") || "";
      const match = disposition.match(/filename="?([^"]+)"?/);
      const filename = match ? match[1] : `${termKey}_grades.csv`;

      const blob = await response.blob();
      const url = window.URL.createObjectURL(blob);
      const link = document.createElement("a");
      link.href = url;
      link.download = filename;
      document.body.appendChild(link);
      link.click();
      link.remove();
      window.URL.revokeObjectURL(url);
    } catch (err) {
      setSaveMessage({ type: "error", text: err.message });
      setTimeout(() => setSaveMessage(null), 4000);
    }
  };

  const handleUploadClick = () => {
    if (!isOverall) fileInputRef.current?.click();
  };

  const handleFileSelected = async (e) => {
    const file = e.target.files?.[0];
    e.target.value = "";
    if (!file || !selectedSectionId || !isCurrentTerm) return;

    const termKey = TERM_KEYS[selectedTerm];
    const formData = new FormData();
    formData.append("file", file);
    formData.append("term", termKey);

    try {
      setIsUploading(true);
      setSaveMessage(null);
      const response = await fetch(`${API_BASE}/sections/${selectedSectionId}/termgrades/csv`, {
        method: "POST",
        headers: { "x-teacher-id": TEACHER_ID },
        body: formData,
      });
      if (!response.ok) {
        const body = await response.json().catch(() => null);
        throw new Error(body?.detail || "Upload failed.");
      }
      const updated = await response.json();
      setRows(updated);
      seedComponents(updated, selectedTerm);
      setSaveMessage({ type: "success", text: "CSV uploaded and computed!" });
    } catch (err) {
      setSaveMessage({ type: "error", text: err.message });
    } finally {
      setIsUploading(false);
      setTimeout(() => setSaveMessage(null), 4000);
    }
  };

  const fmt = (v) => (v === null || v === undefined ? "" : Number(v).toFixed(2));
  const isOverall = selectedTerm === "Overall";
  const termColSpan = gradeComponents.length + 3;

  // academicTerms is sorted latest-first by the backend, so index 0 is
  // always the current, still-open semester. Anything else is a finished
  // semester — grades for it are locked against teacher edits once a
  // newer semester exists.
  const isCurrentTerm = academicTerms.length > 0 && selectedAcademicTerm === encodeTermKey(academicTerms[0]);

  return (
    <div className="h-full pl-[55%] md:pl-88 font-RB">
      <div className="p-10">
        <div>
          <div className="flex gap-2 font-medium text-2xl font-RB">
            <h1>Hello,</h1>
            <h1 className="text-[#DF9409]">{teacherName}</h1>
            <MdWavingHand className="text-[#DF9409]" />
          </div>
          <div className="font-extralight text-xs">
            <p>Select a subject and section to view the class ledger.</p>
          </div>
        </div>

        <div className="flex justify-end items-center gap-3 font-medium mt-4">
          {academicTermsError && <span className="text-sm text-red-600">Failed to load terms: {academicTermsError}</span>}
          {sectionsError && <span className="text-sm text-red-600">Failed to load sections: {sectionsError}</span>}
          {componentsError && <span className="text-sm text-red-600">{componentsError}</span>}

          <select
            value={selectedAcademicTerm}
            onChange={(e) => setSelectedAcademicTerm(e.target.value)}
            disabled={academicTerms.length === 0}
            className="p-3 rounded-lg border border-black/25 cursor-pointer focus:ring-1 focus:ring-green-500 text-sm font-semibold disabled:opacity-50"
          >
            {academicTerms.length === 0 && <option>Loading terms...</option>}
            {academicTerms.map((t) => (
              <option key={encodeTermKey(t)} value={encodeTermKey(t)}>{t.label}</option>
            ))}
          </select>

          <select
            value={selectedSectionId ?? ""}
            onChange={(e) => setSelectedSectionId(e.target.value)}
            disabled={sectionsLoading || sections.length === 0}
            className="p-3 rounded-lg border border-black/25 cursor-pointer focus:ring-1 focus:ring-green-500 text-sm font-semibold disabled:opacity-50"
          >
            {sectionsLoading && <option>Loading sections...</option>}
            {!sectionsLoading && sections.length === 0 && <option>No sections found</option>}
            {sections.map((section) => (
              <option key={section.id} value={section.id}>{section.section}</option>
            ))}
          </select>
        </div>

        <div className="mt-10">
          <div className="w-full h-fit border rounded-2xl p-6 border-[#4E3404]/50">
            <div className="flex flex-wrap justify-between gap-4">
              <div className="flex gap-4">
                <div className="relative w-fit mt-3">
                  <label className="absolute -top-3 left-10 bg-white px-2 text-sm text-gray-500">
                    Select Term
                  </label>
                  <select
                    value={selectedTerm}
                    onChange={(e) => handleTermChange(e.target.value)}
                    className="w-full h-14 rounded-md border border-black/35 px-4 pr-10 font-semibold text-gray-900 focus:outline-none focus:ring-1 focus:ring-green-500"
                  >
                    {TERMS.map((term) => (
                      <option key={term} value={term}>{term}</option>
                    ))}
                    <option value="Overall">Overall</option>
                  </select>
                </div>
              </div>

              <div className="flex space-x-6 h-12.5 mt-3 font-medium">
                {!isOverall && (
                  <>
                    <input
                      type="file"
                      accept=".csv"
                      ref={fileInputRef}
                      onChange={handleFileSelected}
                      className="hidden"
                    />
                    <div
                      onClick={() => isCurrentTerm && handleUploadClick()}
                      className={`bg-white border border-black/12 flex w-44 rounded-xl drop-shadow-lg/25 text-center justify-center gap-2 ${isUploading || !isCurrentTerm ? "opacity-50 cursor-not-allowed" : "cursor-pointer active:scale-95"}`}
                    >
                      <button disabled={isUploading || !isCurrentTerm}>{isUploading ? "Uploading..." : "Upload CSV"}</button>
                      <FiUpload className="mt-4" />
                    </div>
                  </>
                )}

                <div
                  onClick={handleDownloadCSV}
                  className="bg-white border border-black/12 w-44 rounded-xl drop-shadow-lg/25 cursor-pointer active:scale-95 text-center flex justify-center gap-2"
                >
                  <button>Download CSV</button>
                  <LuDownload className="mt-4" />
                </div>

                {!isOverall && (
                  <div
                    className={`border border-black/12 flex w-44 px-8 rounded-xl drop-shadow-lg/25 text-center justify-center ${isSaving || !isCurrentTerm ? "bg-[#3B8126]/50 cursor-not-allowed" : "bg-[#3B8126] cursor-pointer active:scale-95"}`}
                    onClick={() => !isSaving && isCurrentTerm && handleSaveGrades()}
                  >
                    <button className="text-white" disabled={isSaving || !isCurrentTerm}>{isSaving ? "Saving..." : "Save Grades"}</button>
                  </div>
                )}
              </div>
            </div>

            {!isCurrentTerm && (
              <div className="mt-3 text-sm font-medium text-[#996400] bg-[#DF9409]/10 border border-[#DF9409]/40 rounded-lg p-3">
                This semester has ended — grades are locked and shown read-only. Switch to the current semester to make changes.
              </div>
            )}

            {saveMessage && (
              <div className={`mt-3 text-sm font-medium ${saveMessage.type === "success" ? "text-[#3B8126]" : "text-red-600"}`}>
                {saveMessage.text}
              </div>
            )}

            {!isOverall && (
              <div className="overflow-x-auto font-RB mt-15">
                <table className="w-full border-collapse text-sm">
                  <thead>
                    <tr className="w-full border-b border-black/50 text-sm">
                      <th className="font-light text-xs py-2">Student No.</th>
                      <th className="font-light text-xs py-2">Name</th>
                      {gradeComponents.map((c) => (
                        <th key={c.id} className="font-light text-xs py-2">
                          {c.label}
                          <br />
                          <span className="text-[10px] text-gray-400">{c.percentage}%</span>
                        </th>
                      ))}
                      <th className="font-light text-xs py-2">Raw {selectedTerm}</th>
                    </tr>
                  </thead>
                  <tbody>
                    {rowsLoading && (
                      <tr><td colSpan={termColSpan} className="text-center py-8 text-gray-400 text-sm">Loading...</td></tr>
                    )}
                    {!rowsLoading && rowsError && (
                      <tr><td colSpan={termColSpan} className="text-center py-8 text-red-600 text-sm">Failed to load: {rowsError}</td></tr>
                    )}
                    {!rowsLoading && !rowsError && rows.length === 0 && (
                      <tr><td colSpan={termColSpan} className="text-center py-8 text-gray-400 text-sm">No students found for this section.</td></tr>
                    )}

                    {!rowsLoading && !rowsError && rows.map((student) => {
                      const components = getComponents(student.id);
                      const raw = computeTermRawPreview(components, gradeComponents);

                      return (
                        <tr key={student.id} className="border-b font-light text-xs border-gray-200 hover:bg-gray-50">
                          <td className="py-3 px-2">{student.id}</td>
                          <td className="py-3 px-2 whitespace-nowrap">{student.name}</td>

                          {gradeComponents.map((c) => (
                            <td key={c.id} className="py-3 px-2 text-center">
                              <input
                                type="number"
                                min={0}
                                max={100}
                                value={components[c.id] ?? ""}
                                onChange={(e) => handleComponentChange(student.id, c.id, e.target.value)}
                                disabled={!isCurrentTerm}
                                className="w-16 border border-[#4E3404]/50 rounded text-center outline-none bg-[#DF9409]/50 disabled:opacity-50 disabled:cursor-not-allowed"
                              />
                            </td>
                          ))}

                          <td className="py-3 px-2 text-center">
                            <input type="text" readOnly value={raw === null ? "" : raw.toFixed(2)} className="w-16 border rounded text-center bg-gray-50" />
                          </td>
                        </tr>
                      );
                    })}
                  </tbody>
                </table>
              </div>
            )}

            {isOverall && (
              <div className="overflow-x-auto font-RB mt-15">
                <table className="w-full border-collapse text-sm">
                  <thead>
                    <tr className="w-full border-b border-black/50 text-sm">
                      <th className="font-light text-xs py-2">Student No.</th>
                      <th className="font-light text-xs py-2">Name</th>
                      <th className="font-light text-xs py-2">Prelim</th>
                      <th className="font-light text-xs py-2">Midterm</th>
                      <th className="font-light text-xs py-2">Pre-Final</th>
                      <th className="font-light text-xs py-2">Final</th>
                      <th className="font-light text-xs py-2">Equivalent</th>
                    </tr>
                  </thead>
                  <tbody>
                    {rowsLoading && (
                      <tr><td colSpan={7} className="text-center py-8 text-gray-400 text-sm">Loading...</td></tr>
                    )}
                    {!rowsLoading && rows.length === 0 && (
                      <tr><td colSpan={7} className="text-center py-8 text-gray-400 text-sm">No students found for this section.</td></tr>
                    )}

                    {!rowsLoading && rows.map((row) => {
                      const cellClass = (val) =>
                        `w-16 border rounded text-center ${val !== null && val !== undefined && val < 75 ? "bg-[#B22B2D]/50 text-red-900 font-semibold" : "bg-green-100"}`;

                      return (
                        <tr key={row.id} className="border-b font-light text-xs border-gray-200 hover:bg-gray-50">
                          <td className="py-3 px-2">{row.id}</td>
                          <td className="py-3 px-2 whitespace-nowrap">{row.name}</td>
                          <td className="py-3 px-2 text-center"><input type="text" readOnly value={fmt(row.prelim)} className={cellClass(row.prelim)} /></td>
                          <td className="py-3 px-2 text-center"><input type="text" readOnly value={fmt(row.midterm)} className={cellClass(row.midterm)} /></td>
                          <td className="py-3 px-2 text-center"><input type="text" readOnly value={fmt(row.prefinal)} className={cellClass(row.prefinal)} /></td>
                          <td className="py-3 px-2 text-center"><input type="text" readOnly value={fmt(row.final)} className={cellClass(row.final)} /></td>
                          <td className="py-3 px-2 text-center"><input type="text" readOnly value={row.equivalent === null || row.equivalent === undefined ? "" : Number(row.equivalent).toFixed(2)} className="w-16 border rounded text-center bg-gray-50 font-semibold" /></td>
                        </tr>
                      );
                    })}
                  </tbody>
                </table>
              </div>
            )}
          </div>

          <div className="flex space-x-10 pt-6">
            {!isOverall && (
              <div className="flex gap-2 justify-center">
                <FaSquare className="text-[#DF9409]/50 text-center" />
                <h1 className="font-light text-xs">TEACHER - ENTERED</h1>
              </div>
            )}
            {isOverall && (
              <div className="flex gap-2 justify-center">
                <FaSquare className="text-[#3B8126]/50 text-center" />
                <h1 className="font-light text-xs">AUTO - COMPUTED ( 30% PRIOR + 70% RAW )</h1>
              </div>
            )}
            <div className="flex gap-2 justify-center">
              <FaSquare className="text-[#B22B2D]/50 text-center" />
              <h1 className="font-light text-xs">FAILED GRADES</h1>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}

export default Grade;