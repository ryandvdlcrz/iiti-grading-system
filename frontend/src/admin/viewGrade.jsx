import React, { useState, useEffect, useCallback, useRef } from "react";
import { FiSearch, FiDownload } from "react-icons/fi";
import { authHeaders } from "../auth/auth";

const API_BASE = "http://localhost:8000";

const fmt = (v) => (v === null || v === undefined ? "—" : Number(v).toFixed(2));

// A school term (academic year + semester) is encoded as "year|semester"
// for use as a single <select> value, since the two always travel together.
function encodeTermKey(t) {
  return `${t.academic_year}|${t.semester}`;
}
function decodeTermKey(key) {
  const [academic_year, semester] = key.split("|");
  return { academic_year, semester };
}

function ViewGrade() {
  // Filter options (populated from the backend)
  const [options, setOptions] = useState({ courses: [], year_levels: [], sections: [], subjects: [], terms: [] });
  const [optionsError, setOptionsError] = useState(null);

  // Selected filters
  const [course, setCourse] = useState("");
  const [academicTerm, setAcademicTerm] = useState(""); // "year|semester"
  const [yearLevel, setYearLevel] = useState("");
  const [subjectCode, setSubjectCode] = useState("");
  const [section, setSection] = useState("");
  const [searchQuery, setSearchQuery] = useState("");

  // Results
  const [rows, setRows] = useState([]);
  const [hasSearched, setHasSearched] = useState(false);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);
  const [showSectionColumn, setShowSectionColumn] = useState(false);

  // Year Level / Section / Subject are scoped to the selected term, and
  // Subject is further scoped to Year Level + Section once both are
  // picked. Refetch whenever any of those change.
  const fetchOptions = useCallback(async () => {
    try {
      setOptionsError(null);
      const params = new URLSearchParams();
      if (academicTerm) {
        const { academic_year, semester } = decodeTermKey(academicTerm);
        params.set("academic_year", academic_year);
        params.set("semester", semester);
      }
      if (yearLevel && section) {
        params.set("year_level", yearLevel);
        params.set("section", section);
      }
      const response = await fetch(`${API_BASE}/view-grades/filter-options?${params.toString()}`, {
        headers: { ...authHeaders() },
      });
      if (!response.ok) throw new Error(`Failed to load filters (status ${response.status})`);
      const data = await response.json();
      setOptions(data);
      // Default to the most recent term the first time terms load.
      if (!academicTerm && data.terms.length > 0) {
        setAcademicTerm(encodeTermKey(data.terms[0]));
      }
    } catch (err) {
      setOptionsError(err.message);
    }
  }, [academicTerm, yearLevel, section]);

  useEffect(() => {
    fetchOptions();
  }, [fetchOptions]);

  // Set the default course once, the first time options load
  useEffect(() => {
    if (options.courses.length > 0 && !course) setCourse(options.courses[0]);
  }, [options.courses, course]);

  // If the term, year level, or section changes and the currently selected
  // subject is no longer offered to that class, clear it so a stale
  // subject can't stay selected.
  const isFirstOptionsLoad = useRef(true);
  useEffect(() => {
    if (isFirstOptionsLoad.current) {
      isFirstOptionsLoad.current = false;
      return;
    }
    if (subjectCode && !options.subjects.some((s) => s.code === subjectCode)) {
      setSubjectCode("");
    }
  }, [options.subjects, subjectCode]);

  const canSearchByClass = Boolean(academicTerm && subjectCode && yearLevel && section);
  const canSearchByName = Boolean(academicTerm && subjectCode && searchQuery.trim());
  const canSearch = canSearchByClass || canSearchByName;

  const buildParams = useCallback((mode) => {
    const { academic_year, semester } = decodeTermKey(academicTerm);
    const params = new URLSearchParams({
      subject_code: subjectCode,
      course: course || "BSIT",
      academic_year,
      semester,
    });
    if (mode === "class") {
      params.set("year_level", yearLevel);
      params.set("section", section);
    } else {
      params.set("q", searchQuery.trim());
    }
    return params;
  }, [subjectCode, course, academicTerm, yearLevel, section, searchQuery]);

  const runSearch = useCallback(async (mode) => {
    try {
      setLoading(true);
      setError(null);
      setHasSearched(true);
      const params = buildParams(mode);
      const response = await fetch(`${API_BASE}/view-grades?${params.toString()}`, {
        headers: { ...authHeaders() },
      });
      if (!response.ok) {
        const body = await response.json().catch(() => null);
        throw new Error(body?.detail || `Failed to load grades (status ${response.status})`);
      }
      const data = await response.json();
      setRows(data);
      // Name/number search can span multiple sections — show a Section
      // column when it does, so results aren't ambiguous.
      setShowSectionColumn(mode === "name" && new Set(data.map((r) => r.section)).size > 1 && data.some((r) => r.section));
    } catch (err) {
      setError(err.message);
      setRows([]);
    } finally {
      setLoading(false);
    }
  }, [buildParams]);

  // Auto-search as soon as Term + Course + Year Level + Section + Subject
  // are all selected — no button click needed for the class-based lookup.
  useEffect(() => {
    if (canSearchByClass) {
      runSearch("class");
    } else if (!searchQuery.trim()) {
      setHasSearched(false);
      setRows([]);
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [canSearchByClass, academicTerm, course, yearLevel, section, subjectCode]);

  // The search button is only meant for the name/student-no. search.
  const handleSearchClick = () => {
    if (!canSearchByName) return;
    runSearch("name");
  };

  const handleDownloadCSV = async () => {
    if (!canSearch) return;
    try {
      const params = buildParams(canSearchByClass ? "class" : "name");
      const response = await fetch(`${API_BASE}/view-grades/csv?${params.toString()}`, {
        headers: { ...authHeaders() },
      });
      if (!response.ok) throw new Error("Download failed.");

      const disposition = response.headers.get("Content-Disposition") || "";
      const match = disposition.match(/filename="?([^"]+)"?/);
      const filename = match ? match[1] : "grades.csv";

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
      setError(err.message);
    }
  };

  const gradeCellClass = (val) =>
    `w-16 border border-[#4E3404]/50 rounded text-center ${
      val !== null && val !== undefined && val < 75 ? "bg-[#B22B2D]/50 text-red-900 font-semibold" : "bg-green-100"
    }`;

  const rawCellClass = "w-16 border border-[#4E3404]/50 rounded text-center bg-[#DF9409]/20";

  const colCount = 9 + (showSectionColumn ? 1 : 0);

  return (
    <div className="h-full pl-[55%] md:pl-88 font-RB">
      <div className="p-10">
        <div className="flex justify-between">
          <h1 className="text-4xl font-medium">VIEW GRADE</h1>
          <h1 className="font-medium text-[#996400]">ADMIN</h1>
        </div>

        {optionsError && (
          <div className="mt-6 bg-red-50 border border-red-300 text-red-600 text-sm font-medium p-3 rounded-lg">
            {optionsError}
          </div>
        )}

        <div className="mt-10 border border-[#4E3404]/50 rounded-xl p-6 bg-white drop-shadow-lg/25">
          <div className="flex flex-wrap items-end gap-4">
            <div>
              <label className="block text-xs font-medium mb-1">TERM</label>
              <select
                value={academicTerm}
                onChange={(e) => setAcademicTerm(e.target.value)}
                disabled={options.terms.length === 0}
                className="p-3 rounded-lg border border-[#4E3404]/50 w-56 font-medium focus:outline-none focus:ring-1 focus:ring-green-500 disabled:opacity-50"
              >
                {options.terms.length === 0 && <option>Loading terms...</option>}
                {options.terms.map((t) => (
                  <option key={encodeTermKey(t)} value={encodeTermKey(t)}>{t.label}</option>
                ))}
              </select>
            </div>

            <div>
              <label className="block text-xs font-medium mb-1">COURSE</label>
              <select
                value={course}
                onChange={(e) => setCourse(e.target.value)}
                className="p-3 rounded-lg border border-[#4E3404]/50 w-40 font-medium focus:outline-none focus:ring-1 focus:ring-green-500"
              >
                {options.courses.map((c) => (
                  <option key={c} value={c}>{c}</option>
                ))}
              </select>
            </div>

            <div>
              <label className="block text-xs font-medium mb-1">YEAR LEVEL</label>
              <select
                value={yearLevel}
                onChange={(e) => setYearLevel(e.target.value)}
                className="p-3 rounded-lg border border-[#4E3404]/50 w-40 font-medium focus:outline-none focus:ring-1 focus:ring-green-500"
              >
                <option value="">Select year level</option>
                {options.year_levels.map((y) => (
                  <option key={y} value={y}>{y}</option>
                ))}
              </select>
            </div>

            <div>
              <label className="block text-xs font-medium mb-1">SECTION</label>
              <select
                value={section}
                onChange={(e) => setSection(e.target.value)}
                className="p-3 rounded-lg border border-[#4E3404]/50 w-40 font-medium focus:outline-none focus:ring-1 focus:ring-green-500"
              >
                <option value="">Select section</option>
                {options.sections.map((s) => (
                  <option key={s} value={s}>{s}</option>
                ))}
              </select>
            </div>

            <div>
              <label className="block text-xs font-medium mb-1">
                SUBJECT {yearLevel && section ? "" : "(all)"}
              </label>
              <select
                value={subjectCode}
                onChange={(e) => setSubjectCode(e.target.value)}
                className="p-3 rounded-lg border border-[#4E3404]/50 w-56 font-medium focus:outline-none focus:ring-1 focus:ring-green-500"
              >
                <option value="">Select subject</option>
                {options.subjects.map((s) => (
                  <option key={s.code} value={s.code}>{s.code} - {s.title}</option>
                ))}
              </select>
            </div>

            <div className="flex-1 min-w-[200px]">
              <label className="block text-xs font-medium mb-1">
                SEARCH BY NAME / STUDENT NO.
              </label>
              <input
                type="text"
                value={searchQuery}
                onChange={(e) => setSearchQuery(e.target.value)}
                onKeyDown={(e) => { if (e.key === "Enter") handleSearchClick(); }}
                disabled={!subjectCode}
                placeholder={subjectCode ? "e.g. De Guzman" : "Select a subject first"}
                className="p-3 rounded-lg border border-[#4E3404]/50 w-full font-medium focus:outline-none focus:ring-1 focus:ring-green-500 disabled:opacity-50 disabled:bg-gray-100"
              />
            </div>

            <button
              onClick={handleSearchClick}
              disabled={!canSearchByName || loading}
              className="bg-[#3B8126] text-white p-3 rounded-lg active:scale-95 hover:bg-[#2f6d1f] transition disabled:opacity-40 disabled:cursor-not-allowed"
              aria-label="Search"
            >
              <FiSearch className="text-xl" />
            </button>
          </div>

          {error && <p className="text-sm text-red-600 mt-3">{error}</p>}

          {hasSearched && (
            <div className="overflow-x-auto font-RB mt-8">
              <table className="w-full border-collapse text-sm">
                <thead>
                  <tr className="w-full border-b border-black/50 text-sm">
                    <th className="font-light text-xs py-2 text-left">STUDENT NO.</th>
                    <th className="font-light text-xs py-2 text-left">NAME</th>
                    {showSectionColumn && <th className="font-light text-xs py-2">SECTION</th>}
                    <th className="font-light text-xs py-2">PRELIM</th>
                    <th className="font-light text-xs py-2">RAW MIDTERM</th>
                    <th className="font-light text-xs py-2">MIDTERM</th>
                    <th className="font-light text-xs py-2">RAW PRE-FINAL</th>
                    <th className="font-light text-xs py-2">PRE-FINAL</th>
                    <th className="font-light text-xs py-2">RAW FINAL</th>
                    <th className="font-light text-xs py-2">FINAL</th>
                    <th className="font-light text-xs py-2">EQUIVALENT</th>
                  </tr>
                </thead>
                <tbody>
                  {loading && (
                    <tr><td colSpan={colCount} className="text-center py-8 text-gray-400 text-sm">Loading...</td></tr>
                  )}
                  {!loading && rows.length === 0 && !error && (
                    <tr><td colSpan={colCount} className="text-center py-8 text-gray-400 text-sm">No matching students found.</td></tr>
                  )}
                  {!loading && rows.map((row) => (
                    <tr key={`${row.id}-${row.section ?? ""}`} className="border-b font-light text-xs border-gray-200 hover:bg-[#A0FBA3]/10">
                      <td className="py-3 px-2">{row.id}</td>
                      <td className="py-3 px-2 whitespace-nowrap">{row.name}</td>
                      {showSectionColumn && <td className="py-3 px-2 text-center whitespace-nowrap">{row.section ?? "—"}</td>}
                      <td className="py-3 px-2 text-center">
                        <input type="text" readOnly value={fmt(row.prelim)} className={gradeCellClass(row.prelim)} />
                      </td>
                      <td className="py-3 px-2 text-center">
                        <input type="text" readOnly value={fmt(row.raw_midterm)} className={rawCellClass} />
                      </td>
                      <td className="py-3 px-2 text-center">
                        <input type="text" readOnly value={fmt(row.midterm)} className={gradeCellClass(row.midterm)} />
                      </td>
                      <td className="py-3 px-2 text-center">
                        <input type="text" readOnly value={fmt(row.raw_prefinal)} className={rawCellClass} />
                      </td>
                      <td className="py-3 px-2 text-center">
                        <input type="text" readOnly value={fmt(row.prefinal)} className={gradeCellClass(row.prefinal)} />
                      </td>
                      <td className="py-3 px-2 text-center">
                        <input type="text" readOnly value={fmt(row.raw_final)} className={rawCellClass} />
                      </td>
                      <td className="py-3 px-2 text-center">
                        <input type="text" readOnly value={fmt(row.final)} className={gradeCellClass(row.final)} />
                      </td>
                      <td className="py-3 px-2 text-center">
                        <input
                          type="text"
                          readOnly
                          value={row.equivalent === null || row.equivalent === undefined ? "—" : Number(row.equivalent).toFixed(2)}
                          className="w-16 border border-[#4E3404]/50 rounded text-center bg-gray-100 font-semibold"
                        />
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}
        </div>

        {hasSearched && rows.length > 0 && (
          <div className="flex justify-end mt-6">
            <button
              onClick={handleDownloadCSV}
              className="bg-white border border-black/12 flex items-center gap-2 px-6 py-3 rounded-xl drop-shadow-lg/25 cursor-pointer active:scale-95"
            >
              Download CSV <FiDownload />
            </button>
          </div>
        )}
      </div>
    </div>
  );
}

export default ViewGrade;