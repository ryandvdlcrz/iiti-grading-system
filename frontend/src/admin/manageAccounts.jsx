import React, { useState, useEffect, useCallback } from "react";
import { authHeaders } from "../auth/auth";

// Base URL for Python backend
const API_BASE = "http://localhost:8000";

function ManageAccounts() {
  // --- Data fetched from backend ---
  const [professors, setProfessors] = useState([]); // read-only list, used for the name suggestions
  const [accounts, setAccounts] = useState([]); // existing teacher login accounts
  const [loading, setLoading] = useState(true);
  const [loadError, setLoadError] = useState(null);

  const fetchAll = useCallback(async () => {
    try {
      setLoading(true);
      setLoadError(null);

      const headers = { ...authHeaders() };

      const [professorsRes, accountsRes] = await Promise.all([
        fetch(`${API_BASE}/teachers`, { headers }),
        fetch(`${API_BASE}/teacher-accounts`, { headers }),
      ]);

      if (!professorsRes.ok || !accountsRes.ok) {
        throw new Error("Failed to load teacher accounts.");
      }

      const [professorsData, accountsData] = await Promise.all([
        professorsRes.json(),
        accountsRes.json(),
      ]);

      setProfessors(professorsData);
      setAccounts(accountsData);
    } catch (err) {
      setLoadError(err.message);
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    fetchAll();
  }, [fetchAll]);

  // Only suggest professors that don't have an account yet
  const takenProfessorIds = new Set(accounts.map((a) => a.professor_id));
  const availableProfessors = professors.filter(
    (p) => !takenProfessorIds.has(p.id)
  );

  // --- Create Teacher Account form state ---
  const [newTeacherName, setNewTeacherName] = useState("");
  const [newTeacherEmail, setNewTeacherEmail] = useState("");
  const [newTeacherPassword, setNewTeacherPassword] = useState("");
  const [showPassword, setShowPassword] = useState(false);
  const [isAddingTeacher, setIsAddingTeacher] = useState(false);
  const [addTeacherError, setAddTeacherError] = useState(null);

  const canCreate = Boolean(
    newTeacherName.trim() &&
      newTeacherEmail.trim() &&
      newTeacherPassword.length >= 8
  );

  const inputClass =
    "w-full border border-black/50 rounded-full px-4 py-3 text-sm font-normal focus:outline-none focus:border-green-400 focus:ring-2 focus:ring-green-400";

  const handleAddTeacher = async () => {
    if (!canCreate) return;

    // The account must point to a real professor, so the typed name has to
    // match one of the suggestions exactly (case-insensitive).
    const professor = professors.find(
      (p) =>
        p.full_name.trim().toLowerCase() === newTeacherName.trim().toLowerCase()
    );
    if (!professor) {
      setAddTeacherError("Pick a name from the suggestions.");
      return;
    }

    try {
      setIsAddingTeacher(true);
      setAddTeacherError(null);

      const response = await fetch(`${API_BASE}/teacher-accounts`, {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
          ...authHeaders(),
        },
        body: JSON.stringify({
          professor_id: professor.id,
          email: newTeacherEmail.trim(),
          password: newTeacherPassword,
        }),
      });

      if (!response.ok) {
        const body = await response.json().catch(() => null);
        const detail = body?.detail;
        throw new Error(
          typeof detail === "string" ? detail : "Failed to create account."
        );
      }

      setNewTeacherName("");
      setNewTeacherEmail("");
      setNewTeacherPassword("");
      setShowPassword(false);
      await fetchAll();
    } catch (err) {
      setAddTeacherError(err.message);
    } finally {
      setIsAddingTeacher(false);
    }
  };

  return (
    <div className="h-full pl-[55%] md:pl-88 font-RB">
      <div className="p-10">
        {/* Header */}
        <div className="flex justify-between">
          <div className="font-medium">
            <h1 className="text-4xl">Manage Accounts</h1>
            <h1 className="text-xl text-black/50">
              Create and see all teacher accounts
            </h1>
          </div>
          <h1 className="font-medium text-[#996400]">ADMIN</h1>
        </div>

        {loadError && (
          <div className="mt-6 bg-red-50 border border-red-300 text-red-600 text-sm font-medium p-3 rounded-lg">
            {loadError}
          </div>
        )}

        <div className="mt-10 space-y-8">
          {/* Stat card */}
          <div className="w-full max-w-lg border border-[#4E3404]/50 rounded-xl p-6 bg-white drop-shadow-lg/20">
            <p className="text-4xl font-medium">
              {loading ? "-" : accounts.length}
            </p>
            <p className="text-xl text-black/70">Active Teacher Accounts</p>
          </div>

          {/* Teacher Accounts list */}
          <div className="border border-[#4E3404]/50 p-6 rounded-xl font-medium space-y-2 drop-shadow-lg/20 bg-white">
            <h1 className="text-2xl mb-4">Teacher Accounts</h1>

            {loading && (
              <p className="text-sm text-gray-400 py-2">Loading...</p>
            )}

            {!loading && accounts.length === 0 && (
              <p className="text-sm text-gray-400 py-2">
                No teacher accounts yet.
              </p>
            )}

            {!loading &&
              accounts.map((account) => (
                <div
                  key={account.id}
                  className="flex items-center justify-between border-b border-black/50 py-3"
                >
                  <p className="text-base text-black/80">
                    {account.username}
                    <span className="text-black/50"> | {account.email}</span>
                  </p>

                  <div className="flex items-center gap-3">
                    <button
                      disabled
                      title="Reset password (coming soon)"
                      className="w-8 h-8 text-xl flex items-center justify-center disabled:opacity-40 disabled:cursor-not-allowed"
                    >
                      ↺
                    </button>
                    <button
                      disabled
                      title="Delete account (coming soon)"
                      className="w-8 h-8 flex items-center justify-center rounded border border-gray-400 text-gray-500 disabled:opacity-40 disabled:cursor-not-allowed"
                    >
                      ✕
                    </button>
                  </div>
                </div>
              ))}
          </div>

          {/* Create Teacher Accounts */}
          <div className="border border-[#4E3404]/50 p-6 rounded-xl font-medium drop-shadow-lg/20 bg-white">
            <h1 className="text-2xl">Create Teacher Accounts</h1>

            <div className="mt-4 flex flex-col lg:flex-row lg:items-end lg:justify-between gap-6">
              <div className="space-y-4 w-full max-w-sm">
                <div>
                  <label className="block text-sm mb-1 ml-2">Full name</label>
                  <input
                    type="text"
                    list="professor-names"
                    placeholder="Full Name"
                    autoComplete="off"
                    value={newTeacherName}
                    onChange={(e) => setNewTeacherName(e.target.value)}
                    className={inputClass}
                  />
                  <datalist id="professor-names">
                    {availableProfessors.map((p) => (
                      <option key={p.id} value={p.full_name} />
                    ))}
                  </datalist>
                </div>

                <div>
                  <label className="block text-sm mb-1 ml-2">
                    Gmail account
                  </label>
                  <input
                    type="email"
                    placeholder="Enter gmail"
                    autoComplete="off"
                    value={newTeacherEmail}
                    onChange={(e) => setNewTeacherEmail(e.target.value)}
                    className={inputClass}
                  />
                </div>

                <div>
                  <label className="block text-sm mb-1 ml-2">Password</label>
                  <div className="relative">
                    <input
                      type={showPassword ? "text" : "password"}
                      placeholder="Enter password"
                      autoComplete="new-password"
                      value={newTeacherPassword}
                      onChange={(e) => setNewTeacherPassword(e.target.value)}
                      className={`${inputClass} pr-16`}
                    />
                    <button
                      type="button"
                      onClick={() => setShowPassword((prev) => !prev)}
                      className="absolute right-4 top-1/2 -translate-y-1/2 text-xs text-black/50 hover:text-black"
                    >
                      {showPassword ? "Hide" : "Show"}
                    </button>
                  </div>
                  <p className="text-xs text-black/40 mt-1 ml-2">
                    At least 8 characters
                  </p>
                </div>
              </div>

              <button
                onClick={handleAddTeacher}
                disabled={isAddingTeacher || !canCreate}
                className="bg-[#3B8126] text-white px-8 py-3 rounded-lg active:scale-95 hover:bg-[#2f6d1f] transition disabled:opacity-50 disabled:cursor-not-allowed"
              >
                {isAddingTeacher ? "Creating..." : "Create Account"}
              </button>
            </div>

            {addTeacherError && (
              <p className="mt-3 text-sm text-red-600">{addTeacherError}</p>
            )}
          </div>
        </div>
      </div>
    </div>
  );
}

export default ManageAccounts;