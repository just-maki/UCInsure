import React, { useState } from "react";
import { useNavigate } from "react-router-dom";
import "./Upload.css";

type YearFile = {
  yearIndex: number;
  file: File | null;
  progress: number;
};

const Upload: React.FC = () => {
  const navigate = useNavigate();

  const [model, setModel] = useState("");
  const [years, setYears] = useState<number | null>(null);
  const [yearFiles, setYearFiles] = useState<YearFile[]>([]);

  const [draggingIndex, setDraggingIndex] = useState<number | null>(null);

  const [isAnalyzing, setIsAnalyzing] = useState(false);
  const [analysisProgress, setAnalysisProgress] = useState(0);

  const isCSV = (file: File) => {
    return file.name.toLowerCase().endsWith(".csv");
  };

  const handleYearsChange = (value: number) => {
    setYears(value);

    const newSlots: YearFile[] = Array.from({ length: value }).map((_, i) => ({
      yearIndex: i,
      file: null,
      progress: 0
    }));

    setYearFiles(newSlots);
  };

  const simulateUpload = (index: number, file: File) => {
    let progress = 0;

    const interval = setInterval(() => {
      progress += 10;

      setYearFiles((prev) =>
        prev.map((slot) =>
          slot.yearIndex === index ? { ...slot, file, progress } : slot
        )
      );

      if (progress >= 100) clearInterval(interval);
    }, 120);
  };

  const handleFile = (index: number, file: File) => {
    if (!isCSV(file)) {
      alert("Only CSV files are allowed.");
      return;
    }

    simulateUpload(index, file);
  };

  const handleDrop = (e: React.DragEvent<HTMLDivElement>, index: number) => {
    e.preventDefault();
    setDraggingIndex(null);

    if (e.dataTransfer.files && e.dataTransfer.files[0]) {
      handleFile(index, e.dataTransfer.files[0]);
    }
  };

  const removeFile = (index: number) => {
    setYearFiles((prev) =>
      prev.map((slot) =>
        slot.yearIndex === index
          ? { ...slot, file: null, progress: 0 }
          : slot
      )
    );
  };

  // ✅ NEW: require ALL files uploaded
  const allFilesUploaded =
    years !== null &&
    yearFiles.length === years &&
    yearFiles.every((f) => f.file !== null);

  const handleAnalyze = () => {
    setIsAnalyzing(true);

    let progress = 0;
    const interval = setInterval(() => {
      progress += 5;
      setAnalysisProgress(progress);

      if (progress >= 100) {
        clearInterval(interval);

        setTimeout(() => {
          navigate("/analysis", {
            state: {
              model,
              years,
              files: yearFiles
            }
          });
        }, 400);
      }
    }, 120);
  };

  return (
    <div className="upload-container">
      <h2>Configure Analysis</h2>

      <div className="config-section">
        {/* MODEL */}
        <div className="config-row">
          <label>Model: </label>
          <select
            value={model}
            onChange={(e) => setModel(e.target.value)}
            className="styled-select"
          >
            <option value="">Select Model</option>
            <option value="wildfire">Wildfire</option>
            <option value="flood">Flood</option>
            <option value="hurricane">Hurricane</option>
          </select>
        </div>

        {/* YEARS */}
        <div className="config-row">
          <label>Years Into Future: </label>
          <select
            value={years ?? ""}
            onChange={(e) => handleYearsChange(Number(e.target.value))}
            className="styled-select"
          >
            <option value="">Select Years</option>
            {Array.from({ length: 10 }).map((_, i) => (
              <option key={i} value={i + 1}>
                {i + 1} Year{i > 0 && "s"}
              </option>
            ))}
          </select>
        </div>
      </div>

      {/* FILE SECTION */}
      {years && (
        <div className="file-section">
          <h3>Upload Data (Chronological Order)</h3>

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
                <p className="file-name">Year {slot.yearIndex + 1}</p>

                {!slot.file ? (
                  <>
                    <p className="drop-text">Drag & drop CSV here</p>
                    <span>or</span>

                    <label className="upload-button btn">
                      Select File
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
                  </>
                ) : (
                  <>
                    <p>{slot.file.name}</p>

                    {slot.progress < 100 && (
                      <div className="progress-bar">
                        <div
                          className="progress-fill"
                          style={{ width: `${slot.progress}%` }}
                        />
                      </div>
                    )}

                    <button
                      className="delete-btn"
                      onClick={() => removeFile(slot.yearIndex)}
                    >
                      ✕
                    </button>
                  </>
                )}
              </div>
            ))}
          </div>

          {/* ✅ ONLY SHOW WHEN EVERYTHING IS READY */}
          {allFilesUploaded && model && (
            <div className="analyze-container show">
              <button className="analyze-btn btn" onClick={handleAnalyze}>
                Analyze
              </button>
            </div>
          )}
        </div>
      )}

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