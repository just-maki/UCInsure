import React, { useMemo, useState } from "react";
import { useLocation } from "react-router-dom";
import "./AssistantGuide.css";

const PAGE_GUIDE: Record<string, { title: string; prompt: string; questions: Array<{ q: string; a: string }> }> = {
  "/": {
    title: "Home Guide",
    prompt: "Questions about the home page, map, or model choices?",
    questions: [
      {
        q: "What does the home map show?",
        a: "It gives a quick U.S. view of climate-risk intensity bands for flood, wildfire, and hurricane exploration.",
      },
      {
        q: "Which model should I choose?",
        a: "Choose Flood for flood claim records, Wildfire for fire incident or damage data, and Hurricane for wind/property exposure data.",
      },
      {
        q: "Is this only for the U.S.?",
        a: "Yes. The current trained workflow is built around U.S.-based hazard, claims, and property datasets.",
      },
    ],
  },
  "/upload": {
    title: "Upload Guide",
    prompt: "Need help choosing a CSV or model?",
    questions: [
      {
        q: "What file should I upload?",
        a: "Upload a CSV that matches the model you selected. The sample CSV links are the safest reference for column names.",
      },
      {
        q: "Why choose a model first?",
        a: "Each model expects different columns, so the selected model tells the backend how to validate and score the file.",
      },
      {
        q: "Why did analysis fail?",
        a: "The CSV may not match the selected model schema, or the backend may not be running.",
      },
    ],
  },
  "/analysis": {
    title: "Analysis Guide",
    prompt: "Need help reading the results?",
    questions: [
      {
        q: "What is the risk score?",
        a: "It is the average predicted score across all records in the uploaded CSV. Individual records can still be Low, Medium, or High risk.",
      },
      {
        q: "What does the risk distribution mean?",
        a: "It counts how many uploaded properties or records fall into Low, Medium, and High risk groups.",
      },
      {
        q: "What is the future projection?",
        a: "It is a planning scenario based on the uploaded records and an annual hazard trend, not a guaranteed forecast.",
      },
    ],
  },
  "/about": {
    title: "About Guide",
    prompt: "Questions about the team or project goal?",
    questions: [
      {
        q: "What is UCInsure?",
        a: "UCInsure predicts climate-related insurance risk levels using flood, wildfire, and hurricane data workflows.",
      },
      {
        q: "Who is it for?",
        a: "It is useful for students, researchers, insurers, and people comparing climate-risk exposure by location.",
      },
      {
        q: "What is the project goal?",
        a: "The goal is to make climate-risk scoring easier to understand from uploaded insurance or hazard datasets.",
      },
    ],
  },
};

const AssistantGuide: React.FC = () => {
  const location = useLocation();
  const [open, setOpen] = useState(false);
  const guide = useMemo(() => PAGE_GUIDE[location.pathname] ?? PAGE_GUIDE["/"], [location.pathname]);

  return (
    <div className={`assistant-guide ${open ? "is-open" : ""}`}>
      {open && (
        <section className="assistant-panel" aria-label="UCInsure guide">
          <div className="assistant-header">
            <div>
              <span>UCInsure Guide</span>
              <h3>{guide.title}</h3>
            </div>
            <button type="button" onClick={() => setOpen(false)} aria-label="Close guide">
              ×
            </button>
          </div>
          <p className="assistant-prompt">{guide.prompt}</p>
          <div className="assistant-questions">
            {guide.questions.map((item) => (
              <details key={item.q}>
                <summary>{item.q}</summary>
                <p>{item.a}</p>
              </details>
            ))}
          </div>
        </section>
      )}
      <button type="button" className="assistant-toggle" onClick={() => setOpen((value) => !value)}>
        ?
      </button>
    </div>
  );
};

export default AssistantGuide;
