import React, { useState, useEffect, useRef } from "react";
import "./Analysis.css";
import demoGraph from "../assets/demo.png";

const Analysis: React.FC = () => {
  const [showRisk, setShowRisk] = useState(false);
  const [showGraph, setShowGraph] = useState(false);
  const [zoomed, setZoomed] = useState(false);

  const barRef = useRef<HTMLDivElement>(null);

  const riskScoreRaw = 0.9936551249772247;
  const riskScore = riskScoreRaw * 10;
  const riskDisplay = riskScore.toFixed(2);

  const [animatedScore, setAnimatedScore] = useState(0);

  // position clamped 0–100
  const riskPosition = ((animatedScore - 1) / 9) * 90 + 5;
  const riskPositionClamped = Math.min(95, Math.max(5, riskPosition));



  useEffect(() => {
    setTimeout(() => setShowRisk(true), 300);
    setTimeout(() => setShowGraph(true), 800);

    let current = 0;
    const end = riskScore;

    const duration = 1200;
    const steps = 60;
    const increment = (end - current) / steps;

    let i = 0;

    const interval = setInterval(() => {
      current += increment;
      i++;

      if (i >= steps) {
        current = end;
        clearInterval(interval);
      }

      setAnimatedScore(current);
    }, duration / steps);

    return () => clearInterval(interval);
  }, []);

  return (
    <div className="analysis-container">
      <h2>Risk Analysis</h2>

      {/* RISK */}
      <div className={`fade-section ${showRisk ? "show" : ""}`}>
        <div className="risk-section">
          <h3>Predicted Risk Score</h3>
          <p className="risk-value">{riskDisplay}/10</p>

          {/* BAR WRAPPER */}
          <div className="risk-bar-wrapper">
            <div className="risk-bar" ref={barRef}>
              <div className="risk-gradient" />
            </div>

            {/* ARROW (now aligned to bar width properly) */}
            <div
              className={`risk-arrow ${showRisk ? "show" : ""}`}
              style={{ left: `${riskPositionClamped}%` }}
            />
          </div>

          <div className="risk-numbers">
            {[...Array(10)].map((_, i) => (
              <span key={i}>{i + 1}</span>
            ))}
          </div>

          <div className="risk-legend">
            <span><div className="green-box" /> Low</span>
            <span><div className="yellow-box" /> Medium</span>
            <span><div className="red-box" /> High</span>
          </div>
        </div>
      </div>

      {/* GRAPH */}
      <div className={`fade-section ${showGraph ? "show" : ""}`}>
        <div className="graph-section">
          <h3>Model Performance</h3>
          <p className="graph-desc">
            This graph displays how the model’s predicted risk scores compare
            to actual risk levels over the past 5 years.
          </p>

          <img
            src={demoGraph}
            alt="Risk graph"
            className="graph-image"
            onClick={() => setZoomed(true)}
          />
        </div>
      </div>

      {/* ZOOM */}
      {zoomed && (
        <div className="zoom-overlay" onClick={() => setZoomed(false)}>
          <img src={demoGraph} className="zoomed-image" />
        </div>
      )}
    </div>
  );
};

export default Analysis;