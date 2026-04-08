import React from "react";
import "./Footer.css";

const Footer: React.FC = () => {
  return (
    <footer className="footer">
      <div className="footer-content">
        <span className="footer-brand">UCInsure</span>

        <div className="footer-social">
          <a
            href="https://github.com/your-org"
            target="_blank"
            rel="noopener noreferrer"
            aria-label="GitHub"
          >
            GitHub
          </a>
          <a
            href="https://linkedin.com/in/your-profile"
            target="_blank"
            rel="noopener noreferrer"
            aria-label="LinkedIn"
          >
            LinkedIn
          </a>
        </div>
      </div>

      <div className="footer-bottom">
        &copy; {new Date().getFullYear()} UCInsure. All rights reserved.
      </div>
    </footer>
  );
};

export default Footer;