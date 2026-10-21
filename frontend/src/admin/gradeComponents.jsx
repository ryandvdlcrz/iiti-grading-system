import React, { useState, useEffect, useCallback } from "react";
import { authHeaders } from "../auth/auth";

const API_BASE = "http://localhost:8000";

function GradeComponents() {
  const [components, setComponents] = useState([]);
  const [loading, setLoading] = useState(true);
  const [loadError, setLoadError] = useState(null);

  // Local edit buffers, keyed by component id, so typing doesn't fire a
  // save on every keystroke — saved on blur instead.
  const [editBuffers, setEditBuffers] = useState({});
  const [savingId, setSavingId] = useState(null);

  const [newLabel, setNewLabel] = useState("");
  const [newPercentage, setNewPercentage] = useState("");
  const [isAdding, setIsAdding] = useState(false);
  const [addError, setAddError] = useState(null);

  const fetchComponents = useCallback(async () => {
    try {
      setLoading(true);
      setLoadError(null);
      const response = await fetch(`${API_BASE}/grade-components`, {
        headers: { ...authHeaders() },
      });
      if (!response.ok) throw new Error(`Failed to load grade components (status ${response.status})`);
      const data = await response.json();
      setComponents(data);

      const buffers = {};
      data.forEach((c) => {
        buffers[c.id] = { label: c.label, percentage: c.percentage };
      });
      setEditBuffers(buffers);
    } catch (err) {
      setLoadError(err.message);
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    fetchComponents();
  }, [fetchComponents]);

  const totalPercentage = components.reduce((sum, c) => {
    const buffered = editBuffers[c.id];
    const value = buffered ? Number(buffered.percentage) : c.percentage;
    return sum + (isNaN(value) ? 0 : value);
  }, 0);

  const handleBufferChange = (id, field, value) => {
    setEditBuffers((prev) => ({
      ...prev,
      [id]: { ...prev[id], [field]: value },
    }));
  };

  const handleSaveEdit = async (component) => {
    const buffer = editBuffers[component.id];
    if (!buffer) return;

    const label = buffer.label.trim();
    const percentage = Number(buffer.percentage);

    // No-op if nothing actually changed, avoids pointless requests.
    if (label === component.label && percentage === component.percentage) return;

    if (!label) {
      setEditBuffers((prev) => ({ ...prev, [component.id]: { ...prev[component.id], label: component.label } }));
      return;
    }

    try {
      setSavingId(component.id);
      const response = await fetch(`${API_BASE}/grade-components/${component.id}`, {
        method: "PATCH",
        headers: { "Content-Type": "application/json", ...authHeaders() },
        body: JSON.stringify({ label, percentage }),
      });
      if (!response.ok) {
        const body = await response.json().catch(() => null);
        throw new Error(body?.detail || "Failed to update component.");
      }
      await fetchComponents();
    } catch (err) {
      setLoadError(err.message);
    } finally {
      setSavingId(null);
    }
  };

  const handleRemove = async (component) => {
    try {
      const response = await fetch(`${API_BASE}/grade-components/${component.id}`, {
        method: "DELETE",
        headers: { ...authHeaders() },
      });
      if (!response.ok) throw new Error(`Failed to remove component (status ${response.status})`);
      await fetchComponents();
    } catch (err) {
      setLoadError(err.message);
    }
  };

  const handleAdd = async () => {
    const label = newLabel.trim();
    const percentage = Number(newPercentage);

    if (!label) {
      setAddError("Label is required.");
      return;
    }
    if (newPercentage === "" || isNaN(percentage)) {
      setAddError("Percentage is required.");
      return;
    }

    try {
      setIsAdding(true);
      setAddError(null);
      const response = await fetch(`${API_BASE}/grade-components`, {
        method: "POST",
        headers: { "Content-Type": "application/json", ...authHeaders() },
        body: JSON.stringify({ label, percentage }),
      });
      if (!response.ok) {
        const body = await response.json().catch(() => null);
        throw new Error(body?.detail || "Failed to add component.");
      }
      setNewLabel("");
      setNewPercentage("");
      await fetchComponents();
    } catch (err) {
      setAddError(err.message);
    } finally {
      setIsAdding(false);
    }
  };

  return (
    <div className="h-full pl-[55%] md:pl-88 font-RB">
      <div className="p-10">
        <div className="flex justify-between">
          <div className="font-medium">
            <h1 className="text-4xl">Grade Components</h1>
            <h1 className="text-xl text-black/50">
              Edit the label, percentage, and add/remove of each component.
            </h1>
          </div>
          <h1 className="font-medium text-[#996400]">ADMIN</h1>
        </div>

        {loadError && (
          <div className="mt-6 bg-red-50 border border-red-300 text-red-600 text-sm font-medium p-3 rounded-lg">
            {loadError}
          </div>
        )}

        <div className="mt-10 border border-[#4E3404]/50 rounded-xl p-6 bg-white drop-shadow-lg/25">
          {loading && <p className="text-sm text-gray-400 py-4">Loading...</p>}

          {!loading && components.length === 0 && !loadError && (
            <p className="text-sm text-gray-400 py-4">No grade components yet — add one below.</p>
          )}

          {!loading &&
            components.map((component) => {
              const buffer = editBuffers[component.id] || { label: component.label, percentage: component.percentage };
              return (
                <div key={component.id} className="flex items-center gap-4 border-b py-3 last:border-b-0">
                  <input
                    type="text"
                    value={buffer.label}
                    onChange={(e) => handleBufferChange(component.id, "label", e.target.value)}
                    onBlur={() => handleSaveEdit(component)}
                    disabled={savingId === component.id}
                    className="flex-1 border border-black/40 rounded-lg p-3 font-medium focus:outline-none focus:ring-1 focus:ring-green-500 disabled:opacity-50"
                  />

                  <div className="flex items-center gap-1 border border-black/40 rounded-lg px-3 w-28 justify-center">
                    <input
                      type="number"
                      min={0}
                      max={100}
                      value={buffer.percentage}
                      onChange={(e) => handleBufferChange(component.id, "percentage", e.target.value)}
                      onBlur={() => handleSaveEdit(component)}
                      disabled={savingId === component.id}
                      className="w-14 text-center outline-none py-3 disabled:opacity-50"
                    />
                    <span className="text-gray-500">%</span>
                  </div>

                  <button
                    onClick={() => handleRemove(component)}
                    className="w-9 h-9 flex items-center justify-center rounded border border-gray-300 text-gray-500 hover:bg-red-500 hover:text-white transition"
                    aria-label={`Remove ${component.label}`}
                  >
                    ✕
                  </button>
                </div>
              );
            })}

          {!loading && components.length > 0 && (
            <div
              className={`flex justify-between items-center mt-4 p-3 rounded-lg font-medium ${
                totalPercentage === 100 ? "bg-[#A0FBA3]/30" : "bg-red-50 text-red-700"
              }`}
            >
              <span>Total</span>
              <span>{totalPercentage}%</span>
            </div>
          )}

          {!loading && totalPercentage !== 100 && components.length > 0 && (
            <p className="text-xs text-red-600 mt-2">
              Percentages should add up to 100% for grades to compute correctly.
            </p>
          )}

          <div className="flex items-center gap-4 mt-6">
            <input
              type="text"
              placeholder="Label"
              value={newLabel}
              onChange={(e) => setNewLabel(e.target.value)}
              className="flex-1 border rounded-lg p-3 outline-none focus:ring-1 focus:ring-green-500"
            />
            <div className="flex items-center gap-1 border rounded-lg px-3 w-28 justify-center">
              <input
                type="number"
                min={0}
                max={100}
                placeholder="0"
                value={newPercentage}
                onChange={(e) => setNewPercentage(e.target.value)}
                className="w-14 text-center outline-none py-3"
              />
              <span className="text-gray-500">%</span>
            </div>
            <button
              onClick={handleAdd}
              disabled={isAdding}
              className="bg-[#3B8126] text-white px-8 py-3 rounded-lg active:scale-95 hover:bg-[#2f6d1f] transition disabled:opacity-50"
            >
              {isAdding ? "Adding..." : "Add"}
            </button>
          </div>

          {addError && <p className="text-sm text-red-600 mt-2">{addError}</p>}
        </div>
      </div>
    </div>
  );
}

export default GradeComponents;