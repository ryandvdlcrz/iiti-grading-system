import React, { useState, useEffect, useCallback } from "react";
import { authHeaders } from "../auth/auth";

const API_BASE = "http://localhost:8000";

function DeadlineAndReminders() {
  const terms = ["Prelim", "Midterm", "Pre-Final", "Final"];

  const [selectedTerm, setSelectedTerm] = useState(terms[0]);
  const [deadline, setDeadline] = useState("");

  const [deadlinesByTerm, setDeadlinesByTerm] = useState({});
  const [isSaving, setIsSaving] = useState(false);
  const [saveMessage, setSaveMessage] = useState(null);

  const fetchDeadlines = useCallback(async () => {
    try {
      const response = await fetch(`${API_BASE}/deadlines`, {
        headers: { ...authHeaders() },
      });
      if (!response.ok) throw new Error("Failed to load deadlines");
      const data = await response.json();
      const map = {};
      data.forEach((d) => { map[d.term] = d.deadline_date || ""; });
      setDeadlinesByTerm(map);
    } catch (err) {
      setSaveMessage({ type: "error", text: err.message });
    }
  }, []);

  useEffect(() => { fetchDeadlines(); }, [fetchDeadlines]);

  useEffect(() => {
    setDeadline(deadlinesByTerm[selectedTerm] || "");
  }, [selectedTerm, deadlinesByTerm]);

  const handleSaveDeadline = async () => {
    if (!deadline) return;
    try {
      setIsSaving(true);
      setSaveMessage(null);
      const response = await fetch(`${API_BASE}/deadlines`, {
        method: "POST",
        headers: { "Content-Type": "application/json", ...authHeaders() },
        body: JSON.stringify({ term: selectedTerm, deadline_date: deadline }),
      });
      if (!response.ok) {
        const body = await response.json().catch(() => null);
        throw new Error(body?.detail || "Failed to save deadline.");
      }
      setSaveMessage({ type: "success", text: "Deadline saved!" });
      await fetchDeadlines();
    } catch (err) {
      setSaveMessage({ type: "error", text: err.message });
    } finally {
      setIsSaving(false);
      setTimeout(() => setSaveMessage(null), 4000);
    }
  };

  const [reminderLog, setReminderLog] = useState([]);
  const [isSendingReminder, setIsSendingReminder] = useState(false);

  const fetchReminderLog = useCallback(async () => {
    try {
      const response = await fetch(`${API_BASE}/reminders/log`, {
        headers: { ...authHeaders() },
      });
      if (!response.ok) throw new Error("Failed to load reminder log");
      const data = await response.json();
      setReminderLog(data);
    } catch (err) {
      // Non-fatal: reminder log feature isn't on real MongoDB yet.
    }
  }, []);

  useEffect(() => { fetchReminderLog(); }, [fetchReminderLog]);

  const handleSendReminder = async () => {
    try {
      setIsSendingReminder(true);
      setSaveMessage(null);

      const notifResponse = await fetch(`${API_BASE}/notifications`, {
        method: "POST",
        headers: { "Content-Type": "application/json", ...authHeaders() },
        body: JSON.stringify({
          message: `${selectedTerm} grades are due soon${deadline ? ` — please submit by ${deadline}` : ""}.`,
        }),
      });

      if (!notifResponse.ok) {
        throw new Error("Failed to send reminder notification.");
      }

      setSaveMessage({ type: "success", text: "Reminder sent!" });

      try {
        await fetch(`${API_BASE}/reminders/send`, {
          method: "POST",
          headers: { "Content-Type": "application/json", ...authHeaders() },
          body: JSON.stringify({ term: selectedTerm }),
        });
        await fetchReminderLog();
      } catch (logErr) {
        // ignore, admin log is a nice-to-have here
      }
    } catch (err) {
      setSaveMessage({ type: "error", text: err.message });
    } finally {
      setIsSendingReminder(false);
      setTimeout(() => setSaveMessage(null), 4000);
    }
  };

  const today = new Date();
  const dueDays = deadline
    ? Math.ceil((new Date(deadline) - today) / (1000 * 60 * 60 * 24))
    : "";

  return (
    <div className="h-full pl-[55%] md:pl-88 font-RB">
      <div className="p-10">
        <div className="flex justify-between">
          <div className="font-medium">
            <h1 className="text-4xl">Deadlines & Reminders</h1>
            <h1 className="text-xl text-black/50">
              Set the per-term submission deadline and notify teachers.
            </h1>
          </div>
          <h1 className="font-medium text-[#996400]">ADMIN</h1>
        </div>

        <div className="bg-[#3B8126] p-6  rounded-xl text-white mt-25 flex flex-col md:flex-row justify-between items-center gap-4">
          <div>
            {deadline && (
              <>
                <h2 className="text-5xl font-medium">{dueDays} Day(s)</h2>
                <p className="text-xl mt-2 font-medium text-white/80">
                  Until <span className="font-medium">{selectedTerm}</span> grade submission deadline.
                </p>
              </>
            )}
          </div>

          <button
            onClick={handleSendReminder}
            disabled={isSendingReminder}
            className="bg-[#E8A100] active:scale-95 text-black font-semibold px-6 py-3 rounded-lg shadow hover:bg-[#d69500] disabled:opacity-50 disabled:cursor-not-allowed"
          >
            {isSendingReminder ? "Sending..." : "Send Reminder Now"}
          </button>
        </div>

        <div className="mt-8 border border-[#4E3404]/50 p-6 rounded-xl">
          <label className="font-medium">Set Deadline</label>

          <div className="flex flex-col md:flex-row gap-4 mt-6">
            <div className="w-full md:w-auto">
              <select
                value={selectedTerm}
                onChange={(e) => setSelectedTerm(e.target.value)}
                className="w-full md:w-56 p-3 border rounded-lg focus:outline-none focus:ring-2 focus:ring-yellow-500"
              >
                {terms.map((term, index) => (
                  <option key={index} value={term}>{term}</option>
                ))}
              </select>
            </div>

            <div className="w-full md:w-auto">
              <input
                type="date"
                value={deadline}
                onChange={(e) => setDeadline(e.target.value)}
                className="w-full md:w-56 p-3 border rounded-lg focus:outline-none  focus:ring-2 focus:ring-yellow-500"
              />
            </div>

            <div className="w-full md:w-auto">
              <button
                onClick={handleSaveDeadline}
                disabled={isSaving || !deadline}
                className="w-full md:w-auto border border-[#A0FBA3]/20  bg-[#3B8126] text-white p-3 px-8 rounded-xl drop-shadow-lg/50 cursor-pointer active:scale-95 disabled:opacity-50 disabled:cursor-not-allowed"
              >
                {isSaving ? "Saving..." : "Save"}
              </button>
            </div>
          </div>

          {saveMessage && (
            <p className={`mt-3 text-sm font-medium ${saveMessage.type === "success" ? "text-[#3B8126]" : "text-red-600"}`}>
              {saveMessage.text}
            </p>
          )}

          <div className="mt-5 bg-[#A0FBA3]/20 border border-black/40 text-black/50 font-medium p-3 rounded-lg">
            Connects to Calendar automatically once saved — teachers get email +
            in-app reminders as the date nears.
          </div>
        </div>

        <div className="mt-6 border border-[#4E3404]/50 rounded-xl p-6 shadow-sm">
          <div className="flex justify-between items-center mb-5 font-medium">
            <h2 className="font-medium text-2xl">Reminder Log</h2>
            <span className="text-sm text-black/50 mr-9">Status</span>
          </div>

          {reminderLog.length === 0 && (
            <p className="text-sm text-gray-400 py-4">No reminders sent yet.</p>
          )}

          {reminderLog.map((entry) => (
            <div key={entry.id} className="flex justify-between items-center py-3 border-b last:border-b-0">
              <div>
                <h3 className="font-medium text-2xl">
                  {entry.term} deadline reminder sent to {entry.teacher_count} teacher{entry.teacher_count === 1 ? "" : "s"}.
                </h3>
                <p className="text-sm font-light text-black mt-2">{entry.sent_at}</p>
              </div>
              <span className="bg-[#DF9409] text-white px-10 py-2 rounded-lg active:scale-95 text-sm font-semibold">
                {entry.status}
              </span>
            </div>
          ))}
        </div>
      </div>
    </div>
  );
}

export default DeadlineAndReminders;