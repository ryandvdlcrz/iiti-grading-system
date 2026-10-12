import React, { useState, useEffect } from "react";
import { useNavigate } from "react-router-dom";
import { saveSession, getToken, getUser, homePathForRole } from "../auth/auth";

// TODO: change this path to the same logo file your navbar/nav.jsx imports.
import logo from "../assets/navLogo/iitiLogo.png";

// Base URL for Python backend
const API_BASE = "http://localhost:8000";

function Login() {
  const navigate = useNavigate();

  const [identifier, setIdentifier] = useState("");
  const [password, setPassword] = useState("");
  const [isLoggingIn, setIsLoggingIn] = useState(false);
  const [error, setError] = useState(null);

  // Already logged in? Skip the login page.
  useEffect(() => {
    const user = getUser();
    if (getToken() && user) {
      navigate(homePathForRole(user.role), { replace: true });
    }
  }, [navigate]);

  const handleSubmit = async (e) => {
    e.preventDefault();
    if (!identifier.trim() || !password) return;

    try {
      setIsLoggingIn(true);
      setError(null);

      const response = await fetch(`${API_BASE}/auth/login`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ identifier: identifier.trim(), password }),
      });

      const body = await response.json().catch(() => null);

      if (!response.ok) {
        const detail = body?.detail;
        throw new Error(
          typeof detail === "string" ? detail : "Login failed. Please try again."
        );
      }

      saveSession(body.access_token, body.user);
      navigate(homePathForRole(body.user.role), { replace: true });
    } catch (err) {
      setError(
        err instanceof TypeError
          ? "Can't reach the server. Please try again."
          : err.message
      );
    } finally {
      setIsLoggingIn(false);
    }
  };

  const inputClass =
    "w-full h-[43px] rounded-full border border-[#3B8126]/70 px-4 text-sm placeholder:text-black/30 focus:outline-none focus:border-green-500 focus:ring-2 focus:ring-green-400";

  return (
    <div className="min-h-screen bg-[#3B8126] flex items-center justify-center p-6 font-RB">
      <form
        onSubmit={handleSubmit}
        className="w-full max-w-[347px] min-h-[598px] bg-white rounded-3xl px-7 py-8 flex flex-col items-center"
      >
        <img
          src={logo}
          alt="Baliwag Polytechnic College Institute of Information Technology and Innovation"
          className="w-[135px] h-[135px] object-contain"
        />

        <h1 className="mt-4 text-center text-[17px] font-medium leading-snug">
          Institute of Information
          <br />
          Technology and Innovation
        </h1>

        <div className="mt-20 w-full space-y-5">
          <input
            type="text"
            placeholder="User or email account"
            autoComplete="username"
            value={identifier}
            onChange={(e) => setIdentifier(e.target.value)}
            className={inputClass}
          />

          <input
            type="password"
            placeholder="Password"
            autoComplete="current-password"
            value={password}
            onChange={(e) => setPassword(e.target.value)}
            className={inputClass}
          />

          <button
            type="submit"
            disabled={isLoggingIn || !identifier.trim() || !password}
            className="w-full h-[43px] rounded-full bg-[#1A5E00] text-white font-medium hover:bg-[#144a00] active:scale-95 transition disabled:opacity-50 disabled:cursor-not-allowed"
          >
            {isLoggingIn ? "Logging in..." : "Log in"}
          </button>
        </div>

        {error && (
          <p className="mt-6 text-sm text-red-600 text-center">{error}</p>
        )}
      </form>
    </div>
  );
}

export default Login;