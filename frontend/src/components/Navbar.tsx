import React, { useState, useEffect } from "react";
import ReactDOM from "react-dom";
import "./Navbar.css";
import { FontAwesomeIcon } from '@fortawesome/react-fontawesome';
import { faBars, faXmark } from '@fortawesome/free-solid-svg-icons';

const ACCOUNTS_KEY = "ucinsure_accounts";
const CURRENT_USER_KEY = "ucinsure_user";

type Account = {
  name: string;
  email: string;
  passwordHash: string;
};

const MENU = [
  { title: "Home", link: "/" },
  { title: "Uploads", link: "/upload" },
  { title: "Analysis", link: "/analysis" },
  { title: "About", link: "/about" }
];

const validatePassword = (password: string) => {
  if (password.length < 8) return "Password must be at least 8 characters long.";
  if (!/[A-Z]/.test(password)) return "Password must contain at least 1 uppercase letter.";
  if (!/[0-9]/.test(password)) return "Password must contain at least 1 number.";
  if (!/[!@#$%^&*(),.?":{}|<>]/.test(password)) return "Password must contain at least 1 special character.";
  return null;
};

const hashPassword = async (password: string) => {
  const encoder = new TextEncoder();
  const data = encoder.encode(password);
  const hashBuffer = await crypto.subtle.digest("SHA-256", data);
  const hashArray = Array.from(new Uint8Array(hashBuffer));
  return hashArray.map(b => b.toString(16).padStart(2, "0")).join("");
};

const Navbar: React.FC = () => {
  const [isMobileMenuOpen, setIsMobileMenuOpen] = useState(false);
  const [authMode, setAuthMode] = useState<"signin" | "create" | null>(null);
  const [authError, setAuthError] = useState("");
  const [passwordValue, setPasswordValue] = useState("");
  const [user, setUser] = useState<{ name: string; email: string } | null>(() => {
    try {
      const saved = localStorage.getItem(CURRENT_USER_KEY);
      return saved ? JSON.parse(saved) : null;
    } catch {
      return null;
    }
  });

  const passwordChecks = {
    length: passwordValue.length >= 8,
    uppercase: /[A-Z]/.test(passwordValue),
    number: /[0-9]/.test(passwordValue),
    special: /[!@#$%^&*(),.?":{}|<>]/.test(passwordValue),
  };

  useEffect(() => {
    const handleResize = () => {
      if (window.innerWidth > 768) setIsMobileMenuOpen(false);
    };
    window.addEventListener("resize", handleResize);
    return () => window.removeEventListener("resize", handleResize);
  }, []);

  const openAuth = (mode: "signin" | "create") => {
    setAuthMode(mode);
    setAuthError("");
    setPasswordValue("");
    setIsMobileMenuOpen(false);
  };

  const handleAuthSubmit = async (event: React.FormEvent<HTMLFormElement>) => {
    event.preventDefault();

    const form = new FormData(event.currentTarget);
    const name = String(form.get("name") ?? "").trim();
    const email = String(form.get("email") ?? "").trim().toLowerCase();
    const password = String(form.get("password") ?? "");

    if (!email || !password || (authMode === "create" && !name)) {
      setAuthError("Please fill in all required fields.");
      return;
    }

    const savedAccounts = localStorage.getItem(ACCOUNTS_KEY);
    const accounts: Account[] = savedAccounts ? JSON.parse(savedAccounts) : [];

    if (authMode === "create") {
      const exists = accounts.find(a => a.email === email);
      if (exists) { setAuthError("An account with this email already exists."); return; }

      const passwordError = validatePassword(password);
      if (passwordError) { setAuthError(passwordError); return; }

      const passwordHash = await hashPassword(password);
      const newAccount: Account = { name, email, passwordHash };
      const updatedAccounts = [...accounts, newAccount];

      localStorage.setItem(ACCOUNTS_KEY, JSON.stringify(updatedAccounts));
      localStorage.setItem(CURRENT_USER_KEY, JSON.stringify({ name, email }));
      setUser({ name, email });
      setAuthMode(null);
      return;
    }

    const account = accounts.find(a => a.email === email);
    if (!account) { setAuthError("No account found with this email."); return; }

    const passwordHash = await hashPassword(password);
    if (account.passwordHash !== passwordHash) { setAuthError("Incorrect password."); return; }

    localStorage.setItem(CURRENT_USER_KEY, JSON.stringify({ name: account.name, email: account.email }));
    setUser({ name: account.name, email: account.email });
    setAuthMode(null);
  };

  const handleSignOut = () => {
    localStorage.removeItem(CURRENT_USER_KEY);
    setUser(null);
    setIsMobileMenuOpen(false);
  };

  const authModal = authMode ? ReactDOM.createPortal(
    <div className="auth-overlay" onClick={() => setAuthMode(null)}>
      <form className="auth-modal" onSubmit={handleAuthSubmit} onClick={(e) => e.stopPropagation()}>
        <button className="auth-close" type="button" aria-label="Close" onClick={() => setAuthMode(null)}>
          ×
        </button>
        <h2>{authMode === "create" ? "Create Account" : "Sign In"}</h2>
        <p>
          {authMode === "create"
            ? "Create a local demo account for UCInsure."
            : "Sign in with the local account created on this browser."}
        </p>

        {authMode === "create" && (
          <label>
            Name
            <input name="name" type="text" autoComplete="name" />
          </label>
        )}

        <label>
          Email
          <input name="email" type="email" autoComplete="email" />
        </label>

        <label>
          Password
          <input
            name="password"
            type="password"
            autoComplete={authMode === "create" ? "new-password" : "current-password"}
            value={passwordValue}
            onChange={(e) => setPasswordValue(e.target.value)}
          />
          {authMode === "create" && (
            <div className="password-requirements">
              <p className={passwordChecks.length ? "ok" : ""}>• At least 8 characters</p>
              <p className={passwordChecks.uppercase ? "ok" : ""}>• One uppercase letter</p>
              <p className={passwordChecks.number ? "ok" : ""}>• One number</p>
              <p className={passwordChecks.special ? "ok" : ""}>• One special character</p>
            </div>
          )}
        </label>

        {authError && <div className="auth-error">{authError}</div>}

        <button className="auth-submit" type="submit">
          {authMode === "create" ? "Create Account" : "Sign In"}
        </button>

        <button
          className="auth-switch"
          type="button"
          onClick={() => {
            setAuthError("");
            setPasswordValue("");
            setAuthMode(authMode === "create" ? "signin" : "create");
          }}
        >
          {authMode === "create" ? "Already have an account? Sign in" : "Need an account? Create one"}
        </button>
      </form>
    </div>,
    document.body
  ) : null;

  return (
    <>
      <nav className="navbar">
        <div className="logo">UCInsure</div>

        <ul className="desktop-menu">
          {MENU.map(item => (
            <li key={item.title}>
              <a href={item.link}>{item.title}</a>
            </li>
          ))}
        </ul>

        <div className="desktop-buttons">
          {user ? (
            <>
              <span className="user-pill">{user.name}</span>
              <button className="sign-in" type="button" onClick={handleSignOut}>Sign Out</button>
            </>
          ) : (
            <>
              <button className="sign-in" type="button" onClick={() => openAuth("signin")}>Sign In</button>
              <button className="create-account" type="button" onClick={() => openAuth("create")}>Create Account</button>
            </>
          )}
        </div>

        <FontAwesomeIcon className="mobile-menu-button" icon={faBars} onClick={() => setIsMobileMenuOpen(true)} />

        <div className={`mobile-menu-wrapper ${isMobileMenuOpen ? "open" : ""}`}>
          <FontAwesomeIcon className="mobile-close-button" icon={faXmark} onClick={() => setIsMobileMenuOpen(false)} />
          <ul className="mobile-menu">
            {MENU.map(item => (
              <li key={item.title}>
                <a href={item.link} onClick={() => setIsMobileMenuOpen(false)}>{item.title}</a>
              </li>
            ))}
            {user ? (
              <>
                <li className="mobile-user-label">{user.name}</li>
                <li><button type="button" onClick={handleSignOut}>Sign Out</button></li>
              </>
            ) : (
              <>
                <li><button type="button" onClick={() => openAuth("signin")}>Sign In</button></li>
                <li><button type="button" onClick={() => openAuth("create")}>Create Account</button></li>
              </>
            )}
          </ul>
        </div>
      </nav>

      {authModal}
    </>
  );
};

export default Navbar;