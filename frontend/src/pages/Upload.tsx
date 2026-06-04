import React, { useState } from "react";
import { useNavigate } from "react-router-dom";
import "./Upload.css";

type ModelType = "flood" | "hurricane" | "wildfire";

interface ModelInfo {
  label: string;
  icon: string;
  description: string;
  dataSource: string;
  accentColor: string;
}

const MODEL_INFO: Record<ModelType, ModelInfo> = {
  flood: {
    label: "Flood",
    icon: "🌊",
    description:
      "Predicts building damage risk from flood events using FEMA NFIP claims data.",
    dataSource: "FEMA OpenFEMA NFIP Claims CSV",
    accentColor: "#2196f3",
  },
  hurricane: {
    label: "Hurricane",
    icon: "🌀",
    description:
      "Predicts expected annual loss from hurricanes per census tract using NRI data.",
    dataSource: "FEMA National Risk Index (NRI) CSV",
    accentColor: "#9c27b0",
  },
  wildfire: {
    label: "Wildfire",
    icon: "🔥",
    description:
      "Predicts wildfire insurance risk by fire severity using CAL FIRE incident data.",
    dataSource: "Merged CAL FIRE Perimeters + Damage CSV",
    accentColor: "#ff5722",
  },
};

const ANALYSIS_STEPS = [
  "Reading uploaded CSV",
  "Validating model columns",
  "Preparing risk features",
  "Running ML prediction model",
  "Calculating risk distribution",
  "Generating chart and map output",
];

const Upload: React.FC = () => {
  const navigate = useNavigate();

  // Step 1: model selection
  const [selectedModel, setSelectedModel] = useState<ModelType | null>(null);

  // Step 2: file upload
  const [file, setFile] = useState<File | null>(null);
  const [uploadProgress, setUploadProgress] = useState(0);
  const [isDragging, setIsDragging] = useState(false);

  // Analysis state
  const [isAnalyzing, setIsAnalyzing] = useState(false);
  const [analysisProgress, setAnalysisProgress] = useState(0);
  const [analysisStep, setAnalysisStep] = useState(0);

  const isCSV = (f: File) => f.name.toLowerCase().endsWith(".csv");

  const handleFile = (f: File) => {
    if (!isCSV(f)) {
      alert("Only CSV files are allowed.");
      return;
    }
    setFile(f);
    setUploadProgress(0);
    let p = 0;
    const interval = setInterval(() => {
      p += 10;
      setUploadProgress(p);
      if (p >= 100) clearInterval(interval);
    }, 80);
  };

  const handleDrop = (e: React.DragEvent<HTMLDivElement>) => {
    e.preventDefault();
    setIsDragging(false);
    if (e.dataTransfer.files?.[0]) handleFile(e.dataTransfer.files[0]);
  };

  const selectModel = (model: ModelType) => {
    setSelectedModel(model);
    setFile(null);
    setUploadProgress(0);
  };

  const handleAnalyze = async () => {
    if (!file || !selectedModel) return;

    setIsAnalyzing(true);
    setAnalysisProgress(0);
    setAnalysisStep(0);

    let fakeProgress = 0;
    const ticker = setInterval(() => {
      fakeProgress = Math.min(fakeProgress + 3, 88);
      setAnalysisProgress(fakeProgress);
      setAnalysisStep(
        Math.min(
          ANALYSIS_STEPS.length - 1,
          Math.floor((fakeProgress / 100) * ANALYSIS_STEPS.length)
        )
      );
    }, 180);

    try {
      const form = new FormData();
      form.append("file", file);
      form.append("model", selectedModel);

      const response = await fetch("/api/predict", { method: "POST", body: form });

      clearInterval(ticker);

      if (!response.ok) {
        const err = await response
          .json()
          .catch(() => ({ detail: response.statusText }));
        alert(`Analysis failed: ${JSON.stringify(err.detail ?? err)}`);
        setIsAnalyzing(false);
        setAnalysisProgress(0);
        setAnalysisStep(0);
        return;
      }

      const result = await response.json();
      setAnalysisProgress(100);
      setAnalysisStep(ANALYSIS_STEPS.length - 1);
      setTimeout(() => navigate("/analysis", { state: { result } }), 400);
    } catch (err) {
      clearInterval(ticker);
      alert(`Network error: ${err}`);
      setIsAnalyzing(false);
      setAnalysisProgress(0);
      setAnalysisStep(0);
    }
  };

  const info = selectedModel ? MODEL_INFO[selectedModel] : null;

  return (
    <div className="upload-container">
      {/* ── Step 1: Model selection ────────────────────────────────────── */}
      <h2>Choose a Risk Model</h2>
      <p className="upload-subtitle">
        Select the risk model, then upload the matching dataset.
      </p>

      <div className="model-cards">
        {(Object.entries(MODEL_INFO) as [ModelType, ModelInfo][]).map(
          ([key, m]) => (
            <button
              key={key}
              className={`model-card ${selectedModel === key ? "selected" : ""}`}
              style={{ "--card-accent": m.accentColor } as React.CSSProperties}
              onClick={() => selectModel(key)}
            >
              <span className="model-icon">{m.icon}</span>
              <span className="model-label">{m.label}</span>
              <span className="model-desc">{m.description}</span>
              <span className="model-source">{m.dataSource}</span>
            </button>
          )
        )}
      </div>

      {/* ── Step 2: File upload ────────────────────────────────────────── */}
      {selectedModel && info && (
        <>
          <h3 className="upload-step-title">
            Upload {info.label} Dataset
          </h3>

          <div
            className={`drop-zone ${isDragging ? "dragging" : ""}`}
            onDragOver={(e) => {
              e.preventDefault();
              setIsDragging(true);
            }}
            onDragLeave={() => setIsDragging(false)}
            onDrop={handleDrop}
          >
            {file ? (
              <div className="file-ready">
                <span className="file-name-display">📄 {file.name}</span>
                <button
                  className="remove-file-btn"
                  onClick={() => {
                    setFile(null);
                    setUploadProgress(0);
                  }}
                >
                  ✕ Remove
                </button>
              </div>
            ) : (
              <>
                <p>Drag & drop your CSV here</p>
                <span>or</span>
                <label className="upload-button btn">
                  Choose File
                  <input
                    type="file"
                    accept=".csv"
                    hidden
                    onChange={(e) =>
                      e.target.files && handleFile(e.target.files[0])
                    }
                  />
                </label>
                <p className="expected-source">
                  Expected: <em>{info.dataSource}</em>
                </p>
                <a
                  className="sample-download-link"
                  href={`/api/sample/${selectedModel}`}
                  download
                >
                  ⬇ Download sample CSV
                </a>
              </>
            )}
          </div>

          {file && uploadProgress < 100 && (
            <div className="progress-bar upload-progress-bar">
              <div
                className="progress-fill"
                style={{ width: `${uploadProgress}%` }}
              />
            </div>
          )}

          <div
            className={`analyze-container ${
              file && uploadProgress >= 100 ? "show" : ""
            }`}
          >
            <button
              className="analyze-btn btn"
              onClick={handleAnalyze}
              disabled={isAnalyzing}
            >
              {isAnalyzing ? "Analyzing…" : `Analyze ${info.label} Dataset`}
            </button>
          </div>
        </>
      )}

      {/* ── Analysis overlay ───────────────────────────────────────────── */}
      {isAnalyzing && (
        <div className="analysis-overlay">
          <div className="analysis-modal">
            <p className="analysis-kicker">Machine learning pipeline</p>
            <h3>Running {info?.label} Model...</h3>
            <p className="analysis-current-step">{ANALYSIS_STEPS[analysisStep]}</p>
            <div className="analysis-bar">
              <div
                className="analysis-fill"
                style={{ width: `${analysisProgress}%` }}
              />
            </div>
            <p className="analysis-percent">{analysisProgress}% complete</p>
            <div className="analysis-steps">
              {ANALYSIS_STEPS.map((step, index) => (
                <div
                  key={step}
                  className={`analysis-step ${
                    index < analysisStep ? "is-done" : index === analysisStep ? "is-active" : ""
                  }`}
                >
                  <span>{index < analysisStep ? "✓" : index + 1}</span>
                  <p>{step}</p>
                </div>
              ))}
            </div>
          </div>
        </div>
      )}
    </div>
  );
};

export default Upload;
