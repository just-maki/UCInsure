import React, { useState, useEffect, useRef } from "react";
import { useLocation } from "react-router-dom";
import "./Analysis.css";
import demoGraph from "../assets/demo.png";

interface PredictResult {
  avgRisk: number;
  claimCount: number;
  totalDamage: number;
  riskDistribution: { low?: number; medium?: number; high?: number };
  chartUrl: string | null;
  modelUsed: string;
}

const Analysis: React.FC = () => {
  const location = useLocation();
  const apiResult: PredictResult | null = (location.state as { result?: PredictResult })?.result ?? null;

  const [showRisk, setShowRisk] = useState(false);
  const [showGraph, setShowGraph] = useState(false);
  const [zoomed, setZoomed] = useState(false);

  const barRef = useRef<HTMLDivElement>(null);

  // Use API result when available, otherwise fall back to demo values.
  const riskScoreRaw = apiResult?.avgRisk ?? 0.9936551249772247;
  const riskScore = riskScoreRaw * 10;
  const riskDisplay = riskScore.toFixed(2);
  const graphSrc = apiResult?.chartUrl ?? demoGraph;

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
            src={graphSrc}
            alt="Risk graph"
            className="graph-image"
            onClick={() => setZoomed(true)}
          />
        </div>
      </div>

      {/* API METADATA */}
      {apiResult && (
        <div className={`fade-section ${showGraph ? "show" : ""}`}>
          <div className="graph-section">
            <h3>Analysis Summary</h3>
            <table style={{ width: "100%", borderCollapse: "collapse", textAlign: "left" }}>
              <tbody>
                <tr><td><strong>Claims scored</strong></td><td>{apiResult.claimCount.toLocaleString()}</td></tr>
                <tr><td><strong>Total damage paid</strong></td><td>${apiResult.totalDamage.toLocaleString(undefined, { maximumFractionDigits: 0 })}</td></tr>
                <tr><td><strong>Model</strong></td><td>{apiResult.modelUsed}</td></tr>
                {apiResult.riskDistribution && (
                  <tr>
                    <td><strong>Risk distribution</strong></td>
                    <td>
                      Low: {apiResult.riskDistribution.low ?? 0} &nbsp;|
                      Medium: {apiResult.riskDistribution.medium ?? 0} &nbsp;|
                      High: {apiResult.riskDistribution.high ?? 0}
                    </td>
                  </tr>
                )}
              </tbody>
            </table>
          </div>
        </div>
      )}

      {/* ZOOM */}
      {zoomed && (
        <div className="zoom-overlay" onClick={() => setZoomed(false)}>
          <img src={graphSrc} className="zoomed-image" />
        </div>
      )}
    </div>
  );
};

export default Analysis;
