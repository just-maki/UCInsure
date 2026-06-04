import React, { useState, useEffect, useRef } from "react";
import { useLocation, useNavigate } from "react-router-dom";
import RiskMap, { type MapPoint } from "../components/RiskMap";
import jsPDF from "jspdf";
import "./Analysis.css";

interface PredictResult {
  avgRisk: number;
  claimCount: number;
  totalDamage: number;
  riskDistribution: { low?: number; medium?: number; high?: number };
  averageCostByRisk?: { low?: number; medium?: number; high?: number };
  chartUrl: string | null;
  modelUsed: string;
  mapPoints?: MapPoint[];
}

const STORAGE_KEY = "ucinsure_analysis";

const MODEL_META: Record<string, { label: string; cls: string }> = {
  flood:     { label: "Flood",     cls: "badge-flood"     },
  hurricane: { label: "Hurricane", cls: "badge-hurricane" },
  wildfire:  { label: "Wildfire",  cls: "badge-wildfire"  },
};

const downloadPDF = async (result: PredictResult) => {
  const pdf = new jsPDF("p", "mm", "a4");

  const margin = 14;
  let y = 20;

  const addTitle = (text: string) => {
    pdf.setFontSize(16);
    pdf.text(text, margin, y);
    y += 10;
  };

  const addText = (text: string) => {
    pdf.setFontSize(11);
    pdf.text(text, margin, y);
    y += 7;
  };

  const addSectionGap = () => {
    y += 6;
  };

  // HEADER
  addTitle("UCInsure Risk Analysis Report");

  // MODEL
  addText(`Model Used: ${result.modelUsed}`);

  addSectionGap();

  // RISK SCORE
  addTitle("Predicted Risk Score");
  addText(`${(result.avgRisk * 10).toFixed(2)} / 10`);

  addSectionGap();

  // SUMMARY
  addTitle("Analysis Summary");
  addText(`Records Scored: ${result.claimCount.toLocaleString()}`);
  addText(`Total Damage Paid: $${result.totalDamage.toLocaleString()}`);

  addSectionGap();

  // RISK DISTRIBUTION
  addTitle("Properties by Risk Level");
  addText(
    `Low: ${result.riskDistribution.low ?? 0} | ` +
    `Medium: ${result.riskDistribution.medium ?? 0} | ` +
    `High: ${result.riskDistribution.high ?? 0}`
  );

  addSectionGap();

  addTitle("Avg. Cost per Property");
  const fmtUSD = (v: number) =>
  new Intl.NumberFormat("en-US", {
    style: "currency",
    currency: "USD",
    maximumFractionDigits: 0,
  }).format(v ?? 0);

  addText(
    `Low: ${fmtUSD(result.averageCostByRisk?.low ?? 0)} | ` +
    `Medium: ${fmtUSD(result.averageCostByRisk?.medium ?? 0)} | ` +
    `High: ${fmtUSD(result.averageCostByRisk?.high ?? 0)}`
  );
  
  addSectionGap();


  if (result.chartUrl) {
    const img = await fetch(result.chartUrl)
      .then(res => res.blob())
      .then(blob => new Promise<string>((resolve) => {
        const reader = new FileReader();
        reader.onload = () => resolve(reader.result as string);
        reader.readAsDataURL(blob);
      }));

    pdf.addImage(img, "PNG", margin, y, 180, 80);
  }

  pdf.save("ucinsure_analysis.pdf");
};

const GRAPH_COPY: Record<string, { title: string; description: string }> = {
  flood: {
    title: "Flood Risk Chart",
    description:
      "This chart summarizes flood claim records by risk level, using the available claim year information when present.",
  },
  hurricane: {
    title: "Hurricane Risk Trend",
    description:
      "This chart shows the average predicted hurricane risk score by year when valid year information is available.",
  },
  wildfire: {
    title: "Wildfire Risk Chart",
    description:
      "This chart summarizes wildfire incident counts by risk level, using fire year information when available.",
  },
};

function getModelType(modelUsed: string) {
  const m = modelUsed.toLowerCase();
  if (m.startsWith("flood"))     return "flood";
  if (m.startsWith("hurricane")) return "hurricane";
  return "wildfire";
}

const Analysis: React.FC = () => {
  const location = useLocation();
  const navigate = useNavigate();

  const incoming = (location.state as { result?: PredictResult } | null)?.result ?? null;

  const [apiResult, setApiResult] = useState<PredictResult | null>(() => {
    if (incoming) return incoming;
    try {
      const saved = localStorage.getItem(STORAGE_KEY);
      return saved ? (JSON.parse(saved) as PredictResult) : null;
    } catch {
      return null;
    }
  });

  // Persist whenever a fresh result arrives from Upload
  // Falls back to saving without chartUrl if localStorage quota is exceeded
  const _persist = (result: PredictResult) => {
    try {
      localStorage.setItem(STORAGE_KEY, JSON.stringify(result));
    } catch {
      try {
        localStorage.setItem(STORAGE_KEY, JSON.stringify({ ...result, chartUrl: null }));
      } catch { /* storage unavailable */ }
    }
  };

  useEffect(() => {
    if (!incoming) return;
    setApiResult(incoming);
    _persist(incoming);
  }, []); // eslint-disable-line react-hooks/exhaustive-deps

  const handleClear = () => {
    try { localStorage.removeItem(STORAGE_KEY); } catch { /* ignore */ }
    setApiResult(null);
  };

  const [showRisk, setShowRisk] = useState(false);
  const [showGraph, setShowGraph] = useState(false);
  const [zoomed, setZoomed] = useState(false);
  const [animatedScore, setAnimatedScore] = useState(0);

  const barRef = useRef<HTMLDivElement>(null);

  const riskScore = (apiResult?.avgRisk ?? 0) * 10;
  const riskDisplay = riskScore.toFixed(2);
  const graphSrc = apiResult?.chartUrl ?? "";

  // position clamped 0–100
  const riskPosition = ((animatedScore - 1) / 9) * 90 + 5;
  const riskPositionClamped = Math.min(95, Math.max(5, riskPosition));

  useEffect(() => {
    if (!apiResult) return;
    setShowRisk(false);
    setShowGraph(false);
    setAnimatedScore(0);

    const end = apiResult.avgRisk * 10;
    const t1 = setTimeout(() => setShowRisk(true), 300);
    const t2 = setTimeout(() => setShowGraph(true), 800);

    let current = 0;
    const steps = 60;
    const increment = end / steps;
    let i = 0;
    const interval = setInterval(() => {
      current += increment;
      i++;
      if (i >= steps) { current = end; clearInterval(interval); }
      setAnimatedScore(current);
    }, 1200 / steps);

    return () => { clearTimeout(t1); clearTimeout(t2); clearInterval(interval); };
  }, [apiResult]); // eslint-disable-line react-hooks/exhaustive-deps

  // No data: send user back to upload
  if (!apiResult) {
    return (
      <div className="analysis-container">
        <h2>No Analysis Data</h2>
        <p style={{ opacity: 0.7, marginTop: "1rem" }}>
          Upload a dataset and run the analysis to see results here.
        </p>
        <button
          className="analyze-btn btn"
          style={{ marginTop: "2rem" }}
          onClick={() => navigate("/upload")}
        >
          Go to Upload
        </button>
      </div>
    );
  }

  const modelType = getModelType(apiResult.modelUsed);
  const modelMeta = MODEL_META[modelType];
  const graphCopy = GRAPH_COPY[modelType];
  const mapPoints: MapPoint[] = apiResult.mapPoints ?? [];
  const formatCurrency = (value?: number) =>
    `$${(value ?? 0).toLocaleString(undefined, { maximumFractionDigits: 0 })}`;

  return (
    <div className="analysis-container">
      <div className="analysis-header">
        <div className="analysis-title-row">
          <h2>Risk Analysis</h2>
          <span className={`model-badge ${modelMeta.cls}`}>{modelMeta.label}</span>
        </div>
        <div className="analysis-header">
          <div className="analysis-actions">
            <button
              className="download-btn"
              onClick={() => apiResult && downloadPDF(apiResult)}
              >
              ⬇ Download PDF
            </button>
            <button className="clear-btn" onClick={handleClear} title="Remove this analysis">
              ✕ Clear
            </button>
          </div>
        </div>
      </div>

      {/* MAP */}
      <div className={`fade-section map-fade ${showRisk ? "show" : ""}`}>
        <div className="map-section">
          <h3>Geographic Risk Map</h3>
          <p className="graph-desc">
            Each point represents a scored record, coloured by risk level.
            {mapPoints.length === 0 && " (No coordinate data in this dataset.)"}
          </p>
          <RiskMap points={mapPoints} fitPoints={mapPoints.length > 0} />
        </div>
      </div>

      {/* RISK */}
      <div className={`fade-section ${showRisk ? "show" : ""}`}>
        <div className="risk-section">
          <h3>Average Predicted Risk Score</h3>
          <p className="risk-value">{riskDisplay}/10</p>
          <p className="risk-explainer">
            This is the average score for all records in your uploaded CSV. Individual
            properties may still fall into Low, Medium, or High risk.
          </p>

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
          <h3>{graphCopy.title}</h3>
          <p className="graph-desc">
            {graphCopy.description}
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
      <div className={`fade-section ${showGraph ? "show" : ""}`}>
        <div className="graph-section">
          <h3>Analysis Summary</h3>
          <div className="analysis-summary-grid">
            <div className="summary-card">
              <div className="summary-label">Records scored</div>
              <div className="summary-value">
                {apiResult.claimCount.toLocaleString()}
              </div>
            </div>

            <div className="summary-card">
              <div className="summary-label">Total damage</div>
              <div className="summary-value">
                {formatCurrency(apiResult.totalDamage)}
              </div>
            </div>

            <div className="summary-card">
              <div className="summary-label">Model used</div>
              <div className="summary-model">
                {apiResult.modelUsed}
              </div>
            </div>

            {apiResult.riskDistribution && (
              <div className="summary-card wide">
                <div className="summary-label">Properties by risk level</div>
                <div className="summary-distribution">
                  <span>
                    <b>Low:</b> {apiResult.riskDistribution.low ?? 0}
                  </span>
                  <span className="dot">|</span>
                  <span>
                    <b>Medium:</b> {apiResult.riskDistribution.medium ?? 0}
                  </span>
                  <span className="dot">|</span>
                  <span>
                    <b>High:</b> {apiResult.riskDistribution.high ?? 0}
                  </span>
                </div>
              </div>
            )}

            {apiResult.averageCostByRisk && (
              <div className="summary-card wide">
                <div className="summary-label">Avg. cost per property</div>
                <div className="summary-distribution">
                  <span>
                    <b>Low:</b> {formatCurrency(apiResult.averageCostByRisk.low)}
                  </span>
                  <span className="dot">|</span>
                  <span>
                    <b>Medium:</b> {formatCurrency(apiResult.averageCostByRisk.medium)}
                  </span>
                  <span className="dot">|</span>
                  <span>
                    <b>High:</b> {formatCurrency(apiResult.averageCostByRisk.high)}
                  </span>
                </div>
              </div>
            )}

          </div>
        </div>
      </div>

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
