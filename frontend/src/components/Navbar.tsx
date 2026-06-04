import React, { useState, useEffect } from "react";
import "./Navbar.css";
import { FontAwesomeIcon } from '@fortawesome/react-fontawesome';
import { faBars, faXmark } from '@fortawesome/free-solid-svg-icons';

const MENU = [
  { title: "Home", link: "/" },
  { title: "Uploads", link: "/upload" },
  { title: "Analysis", link: "/analysis" },
  { title: "About", link: "/about" }
];

const Navbar: React.FC = () => {
  const [isMobileMenuOpen, setIsMobileMenuOpen] = useState(false);
  const [authMode, setAuthMode] = useState<"signin" | "create" | null>(null);
  const [authError, setAuthError] = useState("");
  const [user, setUser] = useState<{ name: string; email: string } | null>(() => {
    try {
      const saved = localStorage.getItem("ucinsure_user");
      return saved ? JSON.parse(saved) : null;
    } catch {
      return null;
    }
  });

  // Fix #2: close menu when viewport expands past mobile breakpoint
  useEffect(() => {
    const handleResize = () => {
      if (window.innerWidth > 768) {
        setIsMobileMenuOpen(false);
      }
    };
    window.addEventListener("resize", handleResize);
    return () => window.removeEventListener("resize", handleResize);
  }, []);

  const openAuth = (mode: "signin" | "create") => {
    setAuthMode(mode);
    setAuthError("");
    setIsMobileMenuOpen(false);
  };

  const handleAuthSubmit = (event: React.FormEvent<HTMLFormElement>) => {
    event.preventDefault();
    const form = new FormData(event.currentTarget);
    const name = String(form.get("name") ?? "").trim();
    const email = String(form.get("email") ?? "").trim().toLowerCase();
    const password = String(form.get("password") ?? "");

    if (!email || !password || (authMode === "create" && !name)) {
      setAuthError("Please fill in all required fields.");
      return;
    }

    if (authMode === "create") {
      const newUser = { name, email, password };
      localStorage.setItem("ucinsure_account", JSON.stringify(newUser));
      localStorage.setItem("ucinsure_user", JSON.stringify({ name, email }));
      setUser({ name, email });
      setAuthMode(null);
      return;
    }

    try {
      const saved = localStorage.getItem("ucinsure_account");
      const account = saved ? JSON.parse(saved) : null;
      if (!account || account.email !== email || account.password !== password) {
        setAuthError("No matching local account found.");
        return;
      }
      localStorage.setItem("ucinsure_user", JSON.stringify({ name: account.name, email }));
      setUser({ name: account.name, email });
      setAuthMode(null);
    } catch {
      setAuthError("Could not read the saved account.");
    }
  };

  const handleSignOut = () => {
    localStorage.removeItem("ucinsure_user");
    setUser(null);
    setIsMobileMenuOpen(false);
  };

  return (
    <nav className="navbar">
      <div className="logo">UCInsure</div>

      {/* Desktop menu */}
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
            <button className="sign-in" type="button" onClick={handleSignOut}>
              Sign Out
            </button>
          </>
        ) : (
          <>
            <button className="sign-in" type="button" onClick={() => openAuth("signin")}>
              Sign In
            </button>
            <button className="create-account" type="button" onClick={() => openAuth("create")}>
              Create Account
            </button>
          </>
        )}
      </div>

      {/* Hamburger button — only visible on mobile */}
      <FontAwesomeIcon
        className="mobile-menu-button"
        icon={faBars}
        onClick={() => setIsMobileMenuOpen(true)}
      />

      {/* Fix #1: X button and menu are now together inside the overlay */}
      <div className={`mobile-menu-wrapper ${isMobileMenuOpen ? "open" : ""}`}>
        <FontAwesomeIcon
          className="mobile-close-button"
          icon={faXmark}
          onClick={() => setIsMobileMenuOpen(false)}
        />
        <ul className="mobile-menu">
          {MENU.map(item => (
            <li key={item.title}>
              <a href={item.link} onClick={() => setIsMobileMenuOpen(false)}>
                {item.title}
              </a>
            </li>
          ))}
          {/* Fix #3: no sign-in/create-account class here, inherits mobile-menu a styles */}
          {user ? (
            <>
              <li className="mobile-user-label">{user.name}</li>
              <li>
                <button type="button" onClick={handleSignOut}>Sign Out</button>
              </li>
            </>
          ) : (
            <>
              <li>
                <button type="button" onClick={() => openAuth("signin")}>Sign In</button>
              </li>
              <li>
                <button type="button" onClick={() => openAuth("create")}>Create Account</button>
              </li>
            </>
          )}
        </ul>
      </div>

      {authMode && (
        <div className="auth-overlay" onClick={() => setAuthMode(null)}>
          <form className="auth-modal" onSubmit={handleAuthSubmit} onClick={(e) => e.stopPropagation()}>
            <button
              className="auth-close"
              type="button"
              aria-label="Close"
              onClick={() => setAuthMode(null)}
            >
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
              />
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
                setAuthMode(authMode === "create" ? "signin" : "create");
              }}
            >
              {authMode === "create"
                ? "Already have an account? Sign in"
                : "Need an account? Create one"}
            </button>
          </form>
        </div>
      )}
    </nav>
  );
};

export default Navbar;
