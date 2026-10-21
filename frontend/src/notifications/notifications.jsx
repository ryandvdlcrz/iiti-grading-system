import React, { useState, useEffect } from 'react'
import { GoDotFill } from "react-icons/go";

import { IoIosCloseCircleOutline } from "react-icons/io";
import { authHeaders } from "../auth/auth";

// Base URL of the Python backend — same as grade.jsx
const API_BASE = "http://localhost:8000";

function Notifications({ onClose }) {
  const [notifications, setNotifications] = useState([]);
  const [isLoading, setIsLoading] = useState(true);
  const [loadError, setLoadError] = useState(null);

  useEffect(() => {
    async function fetchNotifications() {
      try {
        setIsLoading(true);
        setLoadError(null);

        const response = await fetch(`${API_BASE}/notifications`, {
          headers: { ...authHeaders() },
        });

        if (!response.ok) {
          throw new Error(`Failed to load notifications (status ${response.status})`);
        }

        const data = await response.json();
        setNotifications(data);
      } catch (err) {
        setLoadError(err.message);
      } finally {
        setIsLoading(false);
      }
    }

    fetchNotifications();
  }, []);

  const handleNotificationClick = async (notification) => {
    if (!notification.unread) return; // already read, nothing to do

    // Optimistically mark as read in the UI
    setNotifications((prev) =>
      prev.map((n) => (n.id === notification.id ? { ...n, unread: false } : n))
    );

    try {
      const response = await fetch(
        `${API_BASE}/notifications/${notification.id}/read`,
        {
          method: "POST",
          headers: { ...authHeaders() },
        }
      );

      if (!response.ok) {
        throw new Error("Failed to mark notification as read");
      }
    } catch (err) {
      // Roll back on failure so the UI doesn't lie about the saved state
      setNotifications((prev) =>
        prev.map((n) => (n.id === notification.id ? { ...n, unread: true } : n))
      );
    }
  };

  return (
    <div className="fixed inset-0 bg-black/40 flex font-RB items-center justify-center z-50 p-4">
      {/* The box never grows taller than the screen: the header stays put and only the list scrolls */}
      <div className="bg-white w-fit max-w-full max-h-[85vh] flex flex-col overflow-hidden rounded-xl border-2 border-[#4E3404]/50">

        <div className='flex justify-between p-4 border-b-2 border-gray-300 shrink-0'>

            <h1 className='text-black/50 '>NOTIFICATIONS</h1>

             <button onClick={onClose}>
            <IoIosCloseCircleOutline className='w-6 h-6 active:scale-95 cursor-pointer' />
            </button>

        </div>
        {/*Mensahe mula kay Rene */}
        <div className="overflow-y-auto overscroll-contain min-h-0">

            {isLoading && (
              <p className="p-4 text-sm text-gray-400">Loading...</p>
            )}

            {!isLoading && loadError && (
              <p className="p-4 text-sm text-red-600">{loadError}</p>
            )}

            {!isLoading && !loadError && notifications.length === 0 && (
              <p className="p-4 text-sm text-gray-400">No notifications.</p>
            )}

            <div>
            {!isLoading && !loadError && notifications.map((notification) => (
                <div
                key={notification.id}
                onClick={() => handleNotificationClick(notification)}
                className="p-4  hover:bg-gray-50 cursor-pointer
                             flex  gap-5"
                >
                <div className=''>
                  <GoDotFill
                    className={`text-center text-3xl ${notification.unread ? "text-red-500" : "text-gray-300"}`}
                  />
                </div>  

                <div className=' border-b border-black/20 w-md max-w-full'>
                    <h2 className="font-semibold text-black">
                    {notification.message}
                    </h2>


                    <p className="text-xs text-gray-400 mt-2">
                    {notification.time}
                    </p>
                </div>
                </div>
            ))}
            </div>

        </div>
      </div>
    </div>
  );
}

export default Notifications;