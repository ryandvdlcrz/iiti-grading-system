import React from "react";
import { NavLink, useNavigate } from "react-router-dom";

import IitiLogo from "../assets/navLogo/iitiLogo.png";
import { clearSession } from "../auth/auth";

function NavAdmin() {
  const navigate = useNavigate();

  const activeClass =
    "flex justify-center p-2 border border-white/30 rounded-xl bg-[#067309] drop-shadow-lg/25 active:scale-95";

  const inactiveClass =
    "flex justify-center p-2 rounded-xl hover:bg-white/10 active:scale-95 transition-all";

  const handleLogout = () => {
    clearSession();
    navigate("/login", { replace: true });
  };

  return (
    <aside className="font-RB text-white tracking-wide">
      <div
        className="bg-linear-to-b from-[#3B8126] to-[#175005]
                   fixed h-full w-[45%] md:w-87.5
                   p-6 drop-shadow-lg/50"
      >
        {/* Logo */}
        <div className="flex justify-center my-6">
          <img
            src={IitiLogo}
            alt="IITI Logo"
            className="w-40 h-40"
          />
        </div>

        {/* Navigation */}
        <div className="space-y-6 mt-16">

          {/* Manage Accounts */}
          <NavLink
            to="/admin/manage-accounts"
            className={({ isActive }) =>
              isActive ? activeClass : inactiveClass
            }
          >
            <h1 className="font-medium">Manage Accounts</h1>
          </NavLink>

          {/* Deadlines & Reminders */}
          <NavLink
            to="/admin/deadlines"
            className={({ isActive }) =>
              isActive ? activeClass : inactiveClass
            }
          >
            <h1 className="font-medium">Deadlines & Reminders</h1>
          </NavLink>

          {/* Grade Components */}
          <NavLink
            to="/admin/grade-components"
            className={({ isActive }) =>
              isActive ? activeClass : inactiveClass
            }
          >
            <h1 className="font-medium">Grade Components</h1>
          </NavLink>

          {/* View Grade */}
          <NavLink
            to="/admin/view-grades"
            className={({ isActive }) =>
              isActive ? activeClass : inactiveClass
            }
          >
            <h1 className="font-medium">View Grade</h1>
          </NavLink>
        </div>

        {/* Log out */}
        <div className="absolute bottom-6 left-6 right-6">
          <button
            onClick={handleLogout}
            className="w-full flex justify-center p-2 rounded-xl border border-white/30 hover:bg-white/10 active:scale-95 transition-all"
          >
            <span className="font-medium">Log out</span>
          </button>
        </div>
      </div>
    </aside>
  );
}

export default NavAdmin;