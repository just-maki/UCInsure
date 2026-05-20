import React, { useState } from "react";
import { useNavigate } from "react-router-dom";
import "./Upload.css";

type UploadedFile = {
  file: File;
  progress: number;
  model: string;
};

const Upload: React.FC = () => {
  const navigate = useNavigate();
  const [files, setFiles] = useState<UploadedFile[]>([]);
  const [isDragging, setIsDragging] = useState(false);

  // NEW: analysis state
  const [isAnalyzing, setIsAnalyzing] = useState(false);
  const [analysisProgress, setAnalysisProgress] = useState(0);

  const isCSV = (file: File) => {
    return file.name.toLowerCase().endsWith(".csv");
  };

  const simulateUpload = (file: File) => {
    const newFile: UploadedFile = {
      file,
      progress: 0,
      model: "",
    };

    setFiles((prev) => [...prev, newFile]);

    let progress = 0;
    const interval = setInterval(() => {
      progress += 10;

      setFiles((prev) =>
        prev.map((f) =>
          f.file === file ? { ...f, progress } : f
        )
      );

      if (progress >= 100) clearInterval(interval);
    }, 200);
  };

  const handleFile = (file: File) => {
    if (!isCSV(file)) {
      alert("Only CSV files are allowed.");
      return;
    }

    simulateUpload(file);
  };

  const handleDrop = (e: React.DragEvent<HTMLDivElement>) => {
    e.preventDefault();
    setIsDragging(false);

    if (e.dataTransfer.files && e.dataTransfer.files[0]) {
      handleFile(e.dataTransfer.files[0]);
    }
  };

  const updateModel = (file: File, model: string) => {
    setFiles((prev) =>
      prev.map((f) =>
        f.file === file ? { ...f, model } : f
      )
    );
  };

  const removeFile = (file: File) => {
    setFiles((prev) => prev.filter((f) => f.file !== file));
  };

  const handleAnalyze = async () => {
    // Pick the first file that has a model selected, or fall back to the first file.
    const target = files.find((f) => f.model !== "") ?? files[0];
    if (!target) return;

    setIsAnalyzing(true);
    setAnalysisProgress(0);

    // Animate the progress bar while the request is in-flight.
    let fakeProgress = 0;
    const ticker = setInterval(() => {
      fakeProgress = Math.min(fakeProgress + 4, 85);
      setAnalysisProgress(fakeProgress);
    }, 150);

    try {
      const form = new FormData();
      form.append("file", target.file);
      form.append("model", target.model || "flood");

      const response = await fetch("/api/predict", {
        method: "POST",
        body: form,
      });

      clearInterval(ticker);

      if (!response.ok) {
        const err = await response.json().catch(() => ({ detail: response.statusText }));
        alert(`Analysis failed: ${JSON.stringify(err.detail ?? err)}`);
        setIsAnalyzing(false);
        setAnalysisProgress(0);
        return;
      }

      const result = await response.json();
      setAnalysisProgress(100);

      setTimeout(() => {
        navigate("/analysis", { state: { result } });
      }, 400);
    } catch (err) {
      clearInterval(ticker);
      alert(`Network error: ${err}`);
      setIsAnalyzing(false);
      setAnalysisProgress(0);
    }
  };

  return (
    <div className="upload-container">
      <h2>Upload Your Dataset</h2>

      {/* Drop zone */}
      <div
        className={`drop-zone ${isDragging ? "dragging" : ""}`}
        onDragOver={(e) => {
          e.preventDefault();
          setIsDragging(true);
        }}
        onDragLeave={() => setIsDragging(false)}
        onDrop={handleDrop}
      >
        <p>Drag & drop your CSV file here</p>
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
      </div>

      <div className="file-list">
        {files.map((f, index) => (
          <div key={index} className="file-card">
            <div className="file-info">
              <p className="file-name">{f.file.name}</p>

              {f.progress < 100 && (
                <div className="progress-bar">
                  <div
                    className="progress-fill"
                    style={{ width: `${f.progress}%` }}
                  />
                </div>
              )}
            </div>

            <div className="file-actions">
              <select
                value={f.model}
                onChange={(e) =>
                  updateModel(f.file, e.target.value)
                }
              >
                <option value="">Select Model</option>
                <option value="wildfire">Wildfire</option>
                <option value="flood">Flood</option>
                <option value="hurricane">Hurricane</option>
              </select>

              <button
                className="delete-btn"
                onClick={() => removeFile(f.file)}
              >
                ✕
              </button>
            </div>
          </div>
        ))}
      </div>

      <div className={`analyze-container ${files.length > 0 ? "show" : ""}`}>
        <button className="analyze-btn btn" onClick={handleAnalyze}>
          Analyze Files
        </button>
      </div>

      {isAnalyzing && (
        <div className="analysis-overlay">
          <div className="analysis-modal">
            <h3>Analyzing Data...</h3>

            <div className="analysis-bar">
              <div
                className="analysis-fill"
                style={{ width: `${analysisProgress}%` }}
              />
            </div>

            <p>{analysisProgress}%</p>
          </div>
        </div>
      )}
    </div>
  );
};

export default Upload;
