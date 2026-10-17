// Keeps the logged-in session in the browser so a page refresh doesn't log you out.

const TOKEN_KEY = "auth_token";
const USER_KEY = "auth_user";

export function saveSession(token, user) {
  localStorage.setItem(TOKEN_KEY, token);
  localStorage.setItem(USER_KEY, JSON.stringify(user));
}

export function getToken() {
  return localStorage.getItem(TOKEN_KEY);
}

export function getUser() {
  try {
    return JSON.parse(localStorage.getItem(USER_KEY));
  } catch {
    return null;
  }
}

export function clearSession() {
  localStorage.removeItem(TOKEN_KEY);
  localStorage.removeItem(USER_KEY);
}

// Where each role lands after logging in.
export function homePathForRole(role) {
  return role === "Teacher" ? "/teacher" : "/admin";
}

// Spread this into the headers of every API call:
//   headers: { ...authHeaders() }
//   headers: { "Content-Type": "application/json", ...authHeaders() }
export function authHeaders() {
  const token = getToken();
  return token ? { Authorization: `Bearer ${token}` } : {};
}