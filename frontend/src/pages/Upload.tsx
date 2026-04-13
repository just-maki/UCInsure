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

  const handleAnalyze = () => {
    setIsAnalyzing(true);

    let progress = 0;
    const interval = setInterval(() => {
      progress += 5;
      setAnalysisProgress(progress);

      if (progress >= 100) {
        clearInterval(interval);

        // small delay so it feels smoother
        setTimeout(() => {
          navigate("/analysis", {
            state: { files }
          });
        }, 400);
      }
    }, 150);
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