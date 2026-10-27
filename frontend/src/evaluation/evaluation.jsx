import React, { useState, useEffect } from "react";
import { MdWavingHand } from "react-icons/md";
import { authHeaders } from "../auth/auth";

const API_BASE = import.meta.env.VITE_API_URL || "http://localhost:8000";

function Evaluation() {
  const [teacherName, setTeacherName] = useState("");

  useEffect(() => {
    async function fetchMe() {
      try {
        const response = await fetch(`${API_BASE}/me`, { headers: { ...authHeaders() } });
        if (!response.ok) throw new Error("Failed to load teacher profile");
        const data = await response.json();
        setTeacherName(data.full_name);
      } catch (err) {
        setTeacherName("Teacher");
      }
    }
    fetchMe();
  }, []);

  return (
    <div className="h-full pl-[55%] md:pl-88 font-RB">
      <div className="p-10">
        <div className="flex gap-2 font-medium text-2xl font-RB">
          <h1>Hello,</h1>
          <h1 className="text-[#DF9409]">{teacherName}</h1>
          <MdWavingHand className="text-[#DF9409]" />
        </div>

        <div className="mt-10">
          <div className="w-full min-h-[calc(100vh-14rem)] border rounded-2xl p-6 border-[#4E3404]/50 drop-shadow-lg/25 flex items-center justify-center">
            <div className="w-full max-w-md border border-black rounded-2xl px-10 py-12">
              <h1 className="text-center text-3xl font-medium">Evaluation</h1>

              <div className="mt-10 space-y-6">
                <button
                  className="w-full h-12 rounded-lg bg-[#3B8126] text-white font-medium active:scale-95 hover:bg-[#2f6a1e] transition-all cursor-pointer"
                >
                  Self Evaluation
                </button>
                <button
                  className="w-full h-12 rounded-lg bg-[#3B8126] text-white font-medium active:scale-95 hover:bg-[#2f6a1e] transition-all cursor-pointer"
                >
                  Peer to Peer Evaluation
                </button>
              </div>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}

export default Evaluation;