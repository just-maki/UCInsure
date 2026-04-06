import React, { useState, useEffect } from "react";
import "./Navbar.css";
import { FontAwesomeIcon } from '@fortawesome/react-fontawesome';
import { faBars, faXmark } from '@fortawesome/free-solid-svg-icons';

const MENU = [
  { title: "Home", link: "#" },
  { title: "Uploads", link: "#" },
  { title: "Analysis", link: "#" },
  { title: "About", link: "#" }
];

const Navbar: React.FC = () => {
  const [isMobileMenuOpen, setIsMobileMenuOpen] = useState(false);

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
        <a href="#" className="sign-in">Sign In</a>
        <a href="#" className="create-account">Create Account</a>
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
          <li>
            <a href="#" onClick={() => setIsMobileMenuOpen(false)}>Sign In</a>
          </li>
          <li>
            <a href="#" onClick={() => setIsMobileMenuOpen(false)}>Create Account</a>
          </li>
        </ul>
      </div>
    </nav>
  );
};

export default Navbar;