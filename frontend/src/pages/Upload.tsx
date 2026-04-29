import React, { useState } from "react";
import { useNavigate } from "react-router-dom";
import axios from "axios";
import "./Upload.css";

type YearFile = {
  yearIndex: number;
  file: File | null;
  uploading: boolean;
  uploadProgress: number;
  uploaded: boolean;
  error: boolean;
};

const API_URL = "http://127.0.0.1:8000";

const Upload: React.FC = () => {
  const navigate = useNavigate();

  const [model, setModel] = useState("");
  const [years, setYears] = useState<number | null>(null);
  const [yearFiles, setYearFiles] = useState<YearFile[]>([]);
  const [draggingIndex, setDraggingIndex] = useState<number | null>(null);
  const [isAnalyzing, setIsAnalyzing] = useState(false);
  const [analysisProgress, setAnalysisProgress] = useState(0);

  const isCSV = (file: File) => file.name.toLowerCase().endsWith(".csv");

  // INIT
  const handleYearsChange = (value: number) => {
    setYears(value);
    setYearFiles(
      Array.from({ length: value }).map((_, i) => ({
        yearIndex: i,
        file: null,
        uploading: false,
        uploadProgress: 0,
        uploaded: false,
        error: false
      }))
    );
  };

  // UPLOAD
  const uploadFileToBackend = async (index: number, file: File) => {
    // set immediately so UI updates
    setYearFiles((prev) =>
      prev.map((slot) =>
        slot.yearIndex === index
          ? {
              ...slot,
              file,
              uploading: true,
              uploadProgress: 0,
              uploaded: false,
              error: false
            }
          : slot
      )
    );

    try {
      const formData = new FormData();
      formData.append("file", file);

      await axios.post(`${API_URL}/upload`, formData, {
        // 🚫 DO NOT SET HEADERS HERE

        onUploadProgress: (progressEvent) => {
          if (!progressEvent.total) return;

          const percent = Math.round(
            (progressEvent.loaded * 100) / progressEvent.total
          );

          setYearFiles((prev) =>
            prev.map((slot) =>
              slot.yearIndex === index
                ? { ...slot, uploadProgress: percent }
                : slot
            )
          );
        }
      });

      // success
      setYearFiles((prev) =>
        prev.map((slot) =>
          slot.yearIndex === index
            ? {
                ...slot,
                uploading: false,
                uploaded: true,
                uploadProgress: 100
              }
            : slot
        )
      );
    } catch (err) {
      console.error("UPLOAD ERROR:", err);

      setYearFiles((prev) =>
        prev.map((slot) =>
          slot.yearIndex === index
            ? {
                ...slot,
                uploading: false,
                uploaded: false,
                error: true,
                uploadProgress: 0
              }
            : slot
        )
      );
    }
  };

  const handleFile = async (index: number, file: File) => {
    if (!isCSV(file)) {
      alert("Only CSV files are allowed.");
      return;
    }

    uploadFileToBackend(index, file);
  };

  const handleDrop = (e: React.DragEvent<HTMLDivElement>, index: number) => {
    e.preventDefault();
    setDraggingIndex(null);

    const file = e.dataTransfer.files?.[0];
    if (file) handleFile(index, file);
  };

  const removeFile = (index: number) => {
    setYearFiles((prev) =>
      prev.map((slot) =>
        slot.yearIndex === index
          ? {
              ...slot,
              file: null,
              uploading: false,
              uploadProgress: 0,
              uploaded: false,
              error: false
            }
          : slot
      )
    );
  };

  const allFilesUploaded =
    years !== null &&
    yearFiles.length === years &&
    yearFiles.every((f) => f.uploaded);

  const handleAnalyze = async () => {
    setIsAnalyzing(true);
    setAnalysisProgress(10);

    const payload = {
      model,
      years,
      files: yearFiles.map((f) => ({
        yearIndex: f.yearIndex,
        filename: f.file?.name
      }))
    };

    await axios.post(`${API_URL}/analyze`, payload);

    let progress = 10;
    const interval = setInterval(() => {
      progress += 5;
      setAnalysisProgress(progress);

      if (progress >= 100) {
        clearInterval(interval);
        setTimeout(() => navigate("/analysis", { state: payload }), 300);
      }
    }, 100);
  };

  return (
    <div className="upload-container">
      <h2>Configure Analysis</h2>

      <div className="config-section">
        <div className="config-row">
          <label>Model:</label>
          <select
            className="styled-select"
            value={model}
            onChange={(e) => setModel(e.target.value)}
          >
            <option value="">Select Model</option>
            <option value="wildfire">Wildfire</option>
            <option value="flood">Flood</option>
            <option value="hurricane">Hurricane</option>
          </select>
        </div>

        <div className="config-row">
          <label>Years:</label>
          <select
            className="styled-select"
            value={years ?? ""}
            onChange={(e) => handleYearsChange(Number(e.target.value))}
          >
            <option value="">Select Years</option>
            {Array.from({ length: 10 }).map((_, i) => (
              <option key={i} value={i + 1}>
                {i + 1}
              </option>
            ))}
          </select>
        </div>
      </div>

      {years && (
        <div className="file-section">
          <div className="file-list">
            {yearFiles.map((slot) => (
              <div
                key={slot.yearIndex}
                className={`file-card ${
                  draggingIndex === slot.yearIndex ? "dragging" : ""
                }`}
                onDragOver={(e) => {
                  e.preventDefault();
                  setDraggingIndex(slot.yearIndex);
                }}
                onDragLeave={() => setDraggingIndex(null)}
                onDrop={(e) => handleDrop(e, slot.yearIndex)}
              >
                <p className="year-label">Year {slot.yearIndex + 1}</p>

                {!slot.file && !slot.uploading && (
                  <div className="drop-area">
                    <p className="drop-text">Drag & drop a CSV here, or</p>
                    <label className="upload-button">
                      Browse
                      <input
                        type="file"
                        accept=".csv"
                        hidden
                        onChange={(e) =>
                          e.target.files &&
                          handleFile(slot.yearIndex, e.target.files[0])
                        }
                      />
                    </label>
                  </div>
                )}

                {slot.file && (
                  <div className="file-info">
                    <p className="file-name">📄 {slot.file.name}</p>

                    {(slot.uploading || slot.uploaded) && (
                      <div className="progress-bar">
                        <div
                          className={`progress-fill ${
                            slot.uploaded ? "complete" : ""
                          }`}
                          style={{ width: `${slot.uploadProgress}%` }}
                        />
                      </div>
                    )}

                    <div className="file-status-row">
                      {slot.uploading && (
                        <span className="status uploading">
                          Uploading… {slot.uploadProgress}%
                        </span>
                      )}
                      {slot.uploaded && (
                        <span className="status success">✔ Uploaded</span>
                      )}
                      {slot.error && (
                        <span className="status error">
                          ✖ Upload failed — try again
                        </span>
                      )}

                      {!slot.uploading && (
                        <button
                          className="delete-btn"
                          onClick={() => removeFile(slot.yearIndex)}
                        >
                          ✕ Remove
                        </button>
                      )}
                    </div>
                  </div>
                )}
              </div>
            ))}
          </div>

          <div
            className={`analyze-container ${
              allFilesUploaded && model ? "show" : ""
            }`}
          >
            <button className="analyze-btn" onClick={handleAnalyze}>
              Analyze
            </button>
          </div>
        </div>
      )}

      {isAnalyzing && (
        <div className="analysis-overlay">
          <div className="analysis-modal">
            <h3>Analyzing…</h3>
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