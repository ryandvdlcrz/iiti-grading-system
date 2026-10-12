import React, { useState, useEffect, useCallback } from "react";
import { Link, useLocation } from "react-router-dom";
import IitiLogo from "../assets/navLogo/iitiLogo.png";
import { IoIosNotifications } from "react-icons/io";
import { FaBookBookmark } from "react-icons/fa6";

import Notifications from "../notifications/notifications";

// Same backend/auth constants used by grade.jsx and notifications.jsx
const API_BASE = "http://localhost:8000";
const TEACHER_ID = "6a71ae476300e08da083cd32";

function nav() {
  const [showNotification, setShowNotification] = useState(false);
  const [hasUnread, setHasUnread] = useState(false);

  const checkUnread = useCallback(async () => {
    try {
      const response = await fetch(`${API_BASE}/notifications`, {
        headers: { "x-teacher-id": TEACHER_ID },
      });
      if (!response.ok) return;
      const data = await response.json();
      setHasUnread(data.some((n) => n.unread));
    } catch (err) {
      // Silently ignore — the bell just won't show a dot if this fails
    }
  }, []);

  useEffect(() => {
    checkUnread();
  }, [checkUnread]);

  const handleCloseNotifications = () => {
    setShowNotification(false);
    checkUnread(); // re-check in case something was marked as read
  };

  return (
    <>
      <aside className="font-RB text-white tracking-wide">
        <div
          className="bg-linear-to-b from-[#3B8126] to-[#175005]
                      fixed h-full w-[45%] md:w-87.5
                      p-6 drop-shadow-lg/50"
        >
          {/*IITI LOGO*/}
          <div className="flex justify-center m-6">
            <img
              src={IitiLogo}
              alt="IITI LOGO"
              className="w-39.25 h-39.25"
            />
          </div>

          {/*NAVIGATIONS*/}
          <div className="space-y-10 mt-20">
            {/*GRADE*/}
            <div
              className="space-x-4  flex justify-center p-2 active:scale-95 cursor-pointer
                             border-[0.5px] border-white/27 rounded-xl bg-[#067309] drop-shadow-lg/25"
            >
              <FaBookBookmark className="text-black bg-white p-0.5 w-6 h-6 rounded-md -ml-1" />
              <h1 className="font-medium mr-10">Grades</h1>
            </div>
          </div>
        </div>
      </aside>

      {/*NOTIFICATION ICON - floating, top-right of the page instead of the sidebar*/}
      <button
        onClick={() => setShowNotification(true)}
        className="fixed top-6 right-10 z-40 flex items-center justify-center
                   w-11 h-11 rounded-full bg-white border border-black/10
                   shadow-lg active:scale-95 hover:bg-gray-50 transition-all cursor-pointer"
        aria-label="Notifications"
      >
        <IoIosNotifications className="text-[#175005] w-6 h-6" />
        {hasUnread && (
          <span className="absolute top-1.5 right-1.5 w-2.5 h-2.5 rounded-full bg-red-500 border border-white" />
        )}
      </button>

      {showNotification && (
        <Notifications onClose={handleCloseNotifications} />
      )}
    </>
  );
}

export default nav;