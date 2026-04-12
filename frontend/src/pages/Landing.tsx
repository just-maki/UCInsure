import React from "react";
import { useNavigate } from "react-router-dom";
import "./Landing.css";

const Landing: React.FC = () => {
  const navigate = useNavigate();

  return (
    <div className="landing-container">
      <h1>UCInsure</h1>
      <p className="subtitle">
        Climate risk insurance powered by machine learning.
      </p>

      <p className="description">
        Upload datasets and analyze risk using hurricane, flood, and fire models.
      </p>

      {/* Explanation */}
      <p className="explanation">
        Here's how it works: Upload your CSV datasets, select one of the three 
        actuarial models, analyze the files, and receive a risk score as shown below.
      </p>

      {/* Risk Meter */}
      <div className="risk-meter-container">
        <div className="risk-bar">
          <div className="risk-gradient" />
        </div>

        <div className="risk-numbers">
          {Array.from({ length: 10 }, (_, i) => (
            <span key={i}>{i + 1}</span>
          ))}
        </div>

        {/* Legend */}
        <div className="risk-legend">
          <span><span className="green-box" /> Low Risk</span>
          <span><span className="yellow-box" /> Medium Risk</span>
          <span><span className="red-box" /> High Risk</span>
        </div>
      </div>

      {/* Get Started Button */}
      <button className="get-started-btn" onClick={() => navigate("/upload")}>
        Get Started
      </button>
    </div>
  );
};

export default Landing;