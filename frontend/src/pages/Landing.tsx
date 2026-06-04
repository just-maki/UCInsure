import React, { useEffect, useState } from "react";
import { geoAlbersUsa, geoPath } from "d3-geo";
import { useLocation, useNavigate } from "react-router-dom";
import { feature } from "topojson-client";
import usAtlas from "us-atlas/states-10m.json";
import { FontAwesomeIcon } from "@fortawesome/react-fontawesome";
import { faFireFlameCurved, faDroplet, faWind } from "@fortawesome/free-solid-svg-icons";
import "./Landing.css";

type AtlasFeature = {
  id?: string | number;
};

const normalizeStateId = (stateId: string | number | undefined) => {
  const numericId = Number(String(stateId ?? ""));
  return Number.isNaN(numericId) ? String(stateId ?? "") : String(numericId);
};

const hiddenStateIds = new Set(["2", "15", "60", "66", "69", "72", "78"]);
const stateNames: Record<string, string> = {
  "1": "Alabama", "4": "Arizona", "5": "Arkansas", "6": "California",
  "8": "Colorado", "9": "Connecticut", "10": "Delaware", "11": "District of Columbia",
  "12": "Florida", "13": "Georgia", "16": "Idaho", "17": "Illinois",
  "18": "Indiana", "19": "Iowa", "20": "Kansas", "21": "Kentucky",
  "22": "Louisiana", "23": "Maine", "24": "Maryland", "25": "Massachusetts",
  "26": "Michigan", "27": "Minnesota", "28": "Mississippi", "29": "Missouri",
  "30": "Montana", "31": "Nebraska", "32": "Nevada", "33": "New Hampshire",
  "34": "New Jersey", "35": "New Mexico", "36": "New York", "37": "North Carolina",
  "38": "North Dakota", "39": "Ohio", "40": "Oklahoma", "41": "Oregon",
  "42": "Pennsylvania", "44": "Rhode Island", "45": "South Carolina",
  "46": "South Dakota", "47": "Tennessee", "48": "Texas", "49": "Utah",
  "50": "Vermont", "51": "Virginia", "53": "Washington", "54": "West Virginia",
  "55": "Wisconsin", "56": "Wyoming",
};
const stateRiskTones: Record<string, "low" | "medium" | "elevated" | "high"> = {
  "1": "high", "4": "elevated", "5": "high", "6": "elevated", "8": "medium",
  "9": "elevated", "10": "elevated", "11": "elevated", "12": "high", "13": "high",
  "16": "low", "17": "elevated", "18": "medium", "19": "medium", "20": "medium",
  "21": "elevated", "22": "high", "23": "low", "24": "elevated", "25": "elevated",
  "26": "medium", "27": "medium", "28": "high", "29": "elevated", "30": "low",
  "31": "medium", "32": "medium", "33": "low", "34": "elevated", "35": "elevated",
  "36": "elevated", "37": "high", "38": "low", "39": "medium", "40": "high",
  "41": "low", "42": "elevated", "44": "elevated", "45": "high", "46": "low",
  "47": "elevated", "48": "high", "49": "medium", "50": "low", "51": "elevated",
  "53": "low", "54": "medium", "55": "medium", "56": "low",
};
const riskToneLabels: Record<"low" | "medium" | "elevated" | "high", string> = {
  low: "Low risk", medium: "Moderate risk", elevated: "Elevated risk", high: "High risk",
};

type HoveredState = { id: string; name: string; tone: "low" | "medium" | "elevated" | "high"; x: number; y: number; };
type RegionName = "East Coast" | "West Coast" | "Midwest" | "Gulf Coast" | "Southeast Coast";
type ModelAccent = "flood" | "wildfire" | "hurricane";

const regionStateIds: Record<RegionName, Set<string>> = {
  "East Coast": new Set(["9","10","11","12","13","23","24","25","33","34","36","37","42","44","45","50","51","54"]),
  "West Coast": new Set(["6","16","32","41","49","53"]),
  "Midwest": new Set(["17","18","19","20","26","27","29","31","38","39","46","55"]),
  "Gulf Coast": new Set(["1","12","22","28","48"]),
  "Southeast Coast": new Set(["10","11","12","13","24","37","45","51"]),
};
const modelStateIds: Record<ModelAccent, Set<string>> = {
  flood:     new Set(["1","5","12","17","18","21","22","24","28","29","37","39","42","45","47","48","51","54"]),
  wildfire:  new Set(["4","6","8","16","30","32","35","41","49","53","56"]),
  hurricane: new Set(["1","10","11","12","13","22","24","28","34","36","37","42","45","48","51"]),
};
const welcomeKpis = [
  "Could your next home face flood, wildfire, or hurricane risk?",
  "Could one severe event change insurance cost in your neighborhood?",
  "Which places may look affordable today but carry higher climate exposure?",
  "Can a family compare risk before choosing where to live?",
  "UCInsure turns climate and claim data into a simple risk story.",
];
const welcomeVisualSlides = [
  {
    label: "Wildfire",
    headline: "A wildfire can turn property risk into a family decision overnight.",
    caption: "UCInsure helps translate fire exposure into plain risk levels.",
    image:
      "https://images.unsplash.com/photo-1615092296061-e2ccfeb2f3d6?auto=format&fit=crop&q=80&w=1800",
  },
  {
    label: "Hurricane",
    headline: "A hurricane path can change the cost of protecting a home.",
    caption: "The hurricane model looks at wind, exposure, and location signals.",
    image:
      "https://images.unsplash.com/photo-1527482937786-6608f6e14c15?auto=format&fit=crop&q=80&w=1800",
  },
  {
    label: "Flood",
    headline: "A flooded street is not just weather. It can become a claim.",
    caption: "The flood model summarizes risk from uploaded insurance records.",
    image:
      "https://images.unsplash.com/photo-1475115688296-63fa31716337?auto=format&fit=crop&q=80&w=1800",
  },
];

const atlasData = usAtlas as { objects: { states: unknown } };
const allStates = feature(atlasData as never, atlasData.objects.states as never) as unknown as { features: AtlasFeature[] };
const contiguousStates = allStates.features.filter((s) => !hiddenStateIds.has(normalizeStateId(s.id)));
const projection = geoAlbersUsa().fitExtent([[8, 6], [532, 274]], { type: "FeatureCollection", features: contiguousStates } as never);
const pathGenerator = geoPath(projection);
const getStateTone = (id: string | number | undefined) => stateRiskTones[normalizeStateId(id)] ?? "low";

const Landing: React.FC = () => {
  const navigate = useNavigate();
  const location = useLocation();
  const [hoveredState, setHoveredState] = useState<HoveredState | null>(null);
  const [selectedRegion, setSelectedRegion] = useState<RegionName | null>(null);
  const [selectedModel, setSelectedModel] = useState<ModelAccent | null>(null);
  const [showWelcome, setShowWelcome] = useState(true);
  const [activeWelcomeKpi, setActiveWelcomeKpi] = useState(0);

  useEffect(() => {
    const incoming = (location.state as { selectedModel?: ModelAccent } | null)?.selectedModel;
    if (incoming && ["flood", "wildfire", "hurricane"].includes(incoming)) setSelectedModel(incoming);
  }, [location.state]);

  useEffect(() => {
    if (!showWelcome) return;
    const interval = window.setInterval(() => {
      setActiveWelcomeKpi((current) => (current + 1) % welcomeKpis.length);
    }, 2200);
    return () => window.clearInterval(interval);
  }, [showWelcome]);

  const regions: RegionName[] = ["East Coast", "West Coast", "Midwest", "Gulf Coast", "Southeast Coast"];
  const models = [
    { name: "Flood", accent: "flood" as const, icon: faDroplet },
    { name: "Wildfire", accent: "wildfire" as const, icon: faFireFlameCurved },
    { name: "Hurricane", accent: "hurricane" as const, icon: faWind },
  ];
  const supportedModels = ["Flood Model", "Wildfire Model", "Hurricane Model"];
  const valueProps = [
    "Risk score prediction (1-10 scale)",
    "Interactive geographic risk map",
    "Risk distribution, damage summary, and model chart",
  ];
  const faqs = [
    {
      question: "What file format should I upload?",
      answer:
        "Upload a CSV file. Each model expects a different schema, so the safest option is to choose a model on the Upload page and download its sample CSV to see the required columns.",
    },
    {
      question: "Which model should I choose?",
      answer:
        "Choose Flood for FEMA NFIP-style claim data, Hurricane for wind/property exposure data, and Wildfire for CAL FIRE-style incident data with acreage information.",
    },
    {
      question: "What does the risk score mean?",
      answer:
        "The Analysis page converts the model output into a 1-10 risk score. Higher values mean the uploaded records are being classified as higher risk by the selected model.",
    },
    {
      question: "What is considered Low, Medium, or High risk?",
      answer:
        "The backend uses model scores from 0 to 1. Scores below 0.30 are Low, scores from 0.30 to 0.59 are Medium, and scores of 0.60 or higher are High.",
    },
    {
      question: "What results do I get after analysis?",
      answer:
        "You get a predicted risk score, an interactive geographic risk map when coordinates are available, a model chart, records scored, total damage paid or estimated, model name, and the Low/Medium/High risk distribution.",
    },
    {
      question: "What happens if I upload the wrong dataset?",
      answer:
        "The backend validates the selected model's required columns. If the file does not match the model, the app shows an analysis error instead of producing misleading results.",
    },
    {
      question: "Is this deployed or local-only?",
      answer:
        "Right now the project is local-only. The FastAPI backend runs on localhost:8000 and the Vite frontend runs on localhost:5173.",
    },
  ];

  const COLUMN_HELP: Record<string, string> = {
    dateOfLoss: "Date the flood event occurred and damage was recorded.",
    buildingDamageAmount: "Estimated total structural damage to the building.",
    amountPaidOnBuildingClaim: "Insurance payout for building repairs.",
    amountPaidOnContentsClaim: "Insurance payout for damaged contents inside the property.",
    latitude: "Geographic latitude of the property location.",
    longitude: "Geographic longitude of the property location.",
    state: "U.S. state where the property is located.",
    floodZone: "FEMA flood zone classification such as AE, X, or A.",
    occupancyType: "Type of property use, such as residential or commercial.",
    TRACTFIPS: "Unique census tract identifier used by FEMA.",
    STATE: "Full state name.",
    STATEABBRV: "Two-letter state abbreviation.",
    COUNTY: "County where the tract is located.",
    CENTLAT: "Center latitude of the census tract.",
    CENTLON: "Center longitude of the census tract.",
    AREA: "Land area of the census tract.",
    POPULATION: "Total population in the tract.",
    BUILDVALUE: "Total estimated building or property value.",
    HRCN_EVNTS: "Historical number of hurricane events affecting the tract.",
    HRCN_EALB: "Estimated annual building loss from hurricanes.",
    YEAR_: "Year the wildfire event was recorded.",
    AGENCY: "Agency responsible for reporting the wildfire.",
    UNIT_ID: "Unique identifier for the fire management unit.",
    FIRE_NAME: "Name of the wildfire incident.",
    gis_acres: "Total burned area measured in acres.",
    CAUSE: "Code representing the cause of the fire.",
    DLAT: "Latitude of the fire location.",
    DLON: "Longitude of the fire location.",
    OBJECTIVE: "Fire management objective such as suppression or monitoring.",
  };

  return (
    <main className="landing-page">
      {showWelcome && (
        <div className="welcome-overlay" role="dialog" aria-modal="true" aria-labelledby="welcome-title">
          <div className="presentation-video" aria-hidden="true">
            {welcomeVisualSlides.map((slide, index) => (
              <div
                className="presentation-slide"
                key={slide.label}
                style={{
                  backgroundImage: `linear-gradient(90deg, rgba(2, 6, 23, 0.82), rgba(2, 6, 23, 0.34)), url(${slide.image})`,
                  animationDelay: `${index * 4}s`,
                }}
              >
                <span className="presentation-label">{slide.label}</span>
              </div>
            ))}
          </div>
          <section className="welcome-card welcome-stage">
            <button
              type="button"
              className="welcome-close"
              onClick={() => setShowWelcome(false)}
              aria-label="Close welcome message"
            >
              ×
            </button>
            <div className="welcome-main-copy">
              <p className="welcome-kicker">For every home, there is a climate story</p>
              <h2 id="welcome-title">Would you know if your street was becoming harder to insure?</h2>
              <p className="welcome-copy">
                UCInsure helps families, buyers, and insurers see climate-related risk before a
                flood, wildfire, or hurricane turns into a costly surprise.
              </p>
              <div className="welcome-ticker" aria-live="polite">
                <span>Ask the simple question first</span>
                <strong>{welcomeKpis[activeWelcomeKpi]}</strong>
              </div>
              <div className="welcome-kpi-grid">
                <div>
                  <span>Risk score</span>
                  <strong>1-10</strong>
                </div>
                <div>
                  <span>Hazards</span>
                  <strong>3 models</strong>
                </div>
                <div>
                  <span>Output</span>
                  <strong>Map + cost</strong>
                </div>
              </div>
              <button type="button" className="welcome-primary" onClick={() => setShowWelcome(false)}>
                Enter UCInsure
              </button>
            </div>
            <div className="welcome-disaster-strip" aria-label="Climate risk examples">
              {welcomeVisualSlides.map((slide) => (
                <article className="welcome-disaster-card" key={slide.label}>
                  <img src={slide.image} alt={`${slide.label} risk example`} />
                  <div>
                    <span>{slide.label}</span>
                    <strong>{slide.headline}</strong>
                    <p>{slide.caption}</p>
                  </div>
                </article>
              ))}
            </div>
          </section>
        </div>
      )}

      <section className="landing-hero">
        <article className="dark-card hero-copy-block">
          <h1>Predict. Prepare. Protect.</h1>
          <p className="hero-subtitle">
            AI-powered risk analysis for floods, hurricanes, and wildfires. See what the future holds before it happens.
          </p>
        </article>

        <article className="heatmap-card">
          <div className="section-header">
            <div>
              <p className="section-kicker">Live climate risk heatmap</p>
              <h2>Explore predicted risk intensity across the U.S.</h2>
            </div>
            <span className="map-status">Live</span>
          </div>

          <div className="heatmap-visual">
            <svg viewBox="0 0 540 280" className="heatmap-svg">
              <defs>
                <linearGradient id="oceanGlow" x1="0" y1="0" x2="1" y2="1">
                  <stop offset="0%" stopColor="#0b1520" />
                  <stop offset="100%" stopColor="#071019" />
                </linearGradient>
                <radialGradient id="mapGlowWest" cx="35%" cy="38%" r="44%">
                  <stop offset="0%" stopColor="rgba(45,212,191,0.22)" /><stop offset="100%" stopColor="rgba(45,212,191,0)" />
                </radialGradient>
                <radialGradient id="mapGlowSouth" cx="64%" cy="70%" r="36%">
                  <stop offset="0%" stopColor="rgba(249,115,22,0.2)" /><stop offset="100%" stopColor="rgba(249,115,22,0)" />
                </radialGradient>
                <radialGradient id="mapGlowEast" cx="78%" cy="44%" r="30%">
                  <stop offset="0%" stopColor="rgba(248,113,113,0.28)" /><stop offset="100%" stopColor="rgba(248,113,113,0)" />
                </radialGradient>
              </defs>
              <rect x="0" y="0" width="540" height="280" rx="26" className="heatmap-bg" />
              <g className="map-grid">
                {[40,110,180,250].map((y) => <line key={y} x1="22" y1={y} x2="518" y2={y} />)}
                {[70,150,230,310,390,470].map((x) => <line key={x} x1={x} y1="24" x2={x} y2="256" />)}
              </g>
              <g className="usa-map-group">
                <rect x="8" y="6" width="524" height="268" fill="url(#mapGlowWest)" />
                <rect x="8" y="6" width="524" height="268" fill="url(#mapGlowSouth)" />
                <rect x="8" y="6" width="524" height="268" fill="url(#mapGlowEast)" />
                {contiguousStates.map((state) => {
                  const nid = normalizeStateId(state.id);
                  const isRegionMatch = selectedRegion ? regionStateIds[selectedRegion].has(nid) : false;
                  const isModelMatch  = selectedModel  ? modelStateIds[selectedModel].has(nid)   : false;
                  const isModelDimmed = selectedModel  ? !isModelMatch : false;
                  return (
                    <path
                      key={nid}
                      d={pathGenerator(state as never) ?? ""}
                      className={[
                        "us-state", `tone-${getStateTone(state.id)}`,
                        hoveredState?.id === nid ? "is-hovered" : "",
                        isRegionMatch ? "is-region-selected" : "",
                        isModelMatch  ? "is-model-selected"  : "",
                        isModelDimmed ? "is-model-dimmed"    : "",
                        isRegionMatch && isModelMatch ? "is-both-selected" : "",
                      ].filter(Boolean).join(" ")}
                      onMouseMove={(e) => {
                        const bounds = e.currentTarget.ownerSVGElement?.getBoundingClientRect();
                        if (!bounds) return;
                        setHoveredState({ id: nid, name: stateNames[nid] ?? "Unknown state", tone: getStateTone(nid), x: e.clientX - bounds.left + 12, y: e.clientY - bounds.top - 14 });
                      }}
                      onMouseLeave={() => setHoveredState(null)}
                    />
                  );
                })}
              </g>
            </svg>

            {hoveredState && (
              <div className="map-tooltip" style={{ left: `${hoveredState.x}px`, top: `${hoveredState.y}px` }}>
                <strong>{hoveredState.name}</strong>
                <span>{riskToneLabels[hoveredState.tone]}</span>
              </div>
            )}

            <div className="risk-legend-card">
              <span className="risk-label">Risk level</span>
              <div className="risk-level risk-high"><span />High</div>
              <div className="risk-level risk-elevated"><span />Elevated</div>
              <div className="risk-level risk-medium"><span />Moderate</div>
              <div className="risk-scale">Hover over a state to inspect its assigned risk band.</div>
              <div className="risk-level risk-low"><span />Low</div>
            </div>
          </div>
        </article>
      </section>

      <section className="landing-grid">
        <div className="left-stack">
          <article className="dark-card selector-card">
            <div className="section-header compact">
              <div>
                <h3>Choose a Risk Model</h3>
                <p>Select the type of climate risk you want to analyze.</p>
              </div>
            </div>
            <div className="model-grid">
              {models.map((model) => (
                <button
                  key={model.name}
                  type="button"
                  className={`model-card ${model.accent} ${selectedModel === model.accent ? "is-active" : ""}`}
                  onClick={() => setSelectedModel((cur) => cur === model.accent ? null : model.accent)}
                >
                  <span className="model-icon">
                    <FontAwesomeIcon icon={model.icon} />
                  </span>
                  {model.name}
                </button>
              ))}
            </div>
          </article>

          <article className="dark-card info-card">
            <h3>What You'll Get</h3>
            <ul className="benefits-list">
              {valueProps.map((item) => <li key={item}>{item}</li>)}
            </ul>
          </article>
        </div>

        <div className="right-stack">
          <article className="dark-card selector-card">
            <div className="section-header compact">
              <div>
                <h3>Where are you exploring risk for?</h3>
                <p>Your region helps us provide localized predictions.</p>
              </div>
            </div>
            <div className="chip-group">
              {regions.map((region) => (
                <button
                  key={region}
                  type="button"
                  className={`chip-button ${selectedRegion === region ? "is-active" : ""}`}
                  onClick={() => setSelectedRegion((cur) => cur === region ? null : region)}
                >
                  {region}
                </button>
              ))}
            </div>
          </article>

          <article className="upload-card-large">
            <div className="section-header compact">
              <div>
                <h3>Upload Your CSV Dataset to Get Started</h3>
                <p>Drag and drop your file or browse locally.</p>
              </div>
            </div>
            <button
              type="button"
              className="upload-dropzone"
              onClick={() => navigate("/upload", { state: { selectedModel } })}
            >
              <span className="upload-icon">&#8682;</span>
              <strong>Drag &amp; drop your CSV file here</strong>
              <span>or click to browse</span>
            </button>
            <p className="security-note">Your data is secure and confidential.</p>
          </article>

          <article className="dark-card supported-card">
            <h3>Supported Models</h3>
            <ul className="supported-list">
              {supportedModels.map((item) => <li key={item}>{item}</li>)}
            </ul>
            <p className="trusted-note">Trusted by researchers, insurers, and communities.</p>
          </article>
        </div>
      </section>

      <section className="csv-section">
        <div className="faq-header">
          <p className="section-kicker">Data Format Guide</p>
          <h2>Required CSV Structure by Model</h2>
        </div>

        <div className="csv-grid">
          <div className="csv-card flood">
            <h3>Flood Model</h3>
            <p className="csv-sub">FEMA NFIP Claims Dataset</p>
            <table>
              <tbody>
                {[
                  "dateOfLoss",
                  "buildingDamageAmount",
                  "amountPaidOnBuildingClaim",
                  "amountPaidOnContentsClaim",
                  "latitude",
                  "longitude",
                  "state",
                  "floodZone",
                  "occupancyType",
                ].map((col) => (
                  <tr key={col}>
                    <td className="csv-cell">
                      <span className="csv-tooltip-wrapper">
                        <span className="csv-hover">{col}</span>
                        <span className="csv-tooltip">{COLUMN_HELP[col]}</span>
                      </span>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>

          <div className="csv-card hurricane">
            <h3>Hurricane Model</h3>
            <p className="csv-sub">FEMA NRI Census Tracts</p>
            <table>
              <tbody>
                {[
                  "TRACTFIPS",
                  "STATE",
                  "STATEABBRV",
                  "COUNTY",
                  "CENTLAT",
                  "CENTLON",
                  "AREA",
                  "POPULATION",
                  "BUILDVALUE",
                  "HRCN_EVNTS",
                  "HRCN_EALB",
                ].map((col) => (
                  <tr key={col}>
                    <td className="csv-cell">
                      <span className="csv-tooltip-wrapper">
                        <span className="csv-hover">{col}</span>
                        <span className="csv-tooltip">{COLUMN_HELP[col]}</span>
                      </span>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>

          <div className="csv-card wildfire">
            <h3>Wildfire Model</h3>
            <p className="csv-sub">CAL FIRE Incident Data</p>
            <table>
              <tbody>
                {[
                  "YEAR_",
                  "STATE",
                  "AGENCY",
                  "UNIT_ID",
                  "FIRE_NAME",
                  "gis_acres",
                  "CAUSE",
                  "DLAT",
                  "DLON",
                  "COUNTY",
                  "OBJECTIVE",
                ].map((col) => (
                  <tr key={col}>
                    <td className="csv-cell">
                      <span className="csv-tooltip-wrapper">
                        <span className="csv-hover">{col}</span>
                        <span className="csv-tooltip">{COLUMN_HELP[col]}</span>
                      </span>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>
      </section>

      <section className="faq-section">
        <div className="faq-header">
          <p className="section-kicker">Project FAQ</p>
          <h2>Frequently Asked Questions</h2>
        </div>

        <div className="faq-list">
          {faqs.map((item) => (
            <details className="faq-item" key={item.question}>
              <summary>
                <span className="faq-q">Q.</span>
                <span>{item.question}</span>
              </summary>
              <p>{item.answer}</p>
            </details>
          ))}
        </div>
      </section>
    </main>
  );
};

export default Landing;
