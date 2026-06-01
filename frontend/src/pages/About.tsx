import React from "react";
import "./About.css";
import asmitaPhoto from "../assets/team/asmita.jpg";
import eshaPhoto from "../assets/team/esha.jpg";
import maxPhoto from "../assets/team/max.jpg";
import vishakhaPhoto from "../assets/team/vishakha.jpg";

interface TeamMember {
  name: string;
  role: string;
  area: string;
  accent: string;
  initials: string;
  photo: string;
  linkedin: string;
}

const TEAM: TeamMember[] = [
  {
    name: "Vishakha Mishra",
    role: "Model Creator",
    area: "Flood Risk Model",
    accent: "#2196f3",
    initials: "VM",
    photo: vishakhaPhoto,
    linkedin: "https://www.linkedin.com/in/vishakha-m-009626239/",
  },
  {
    name: "Asmita Gawde",
    role: "Model Creator",
    area: "Wildfire Risk Model",
    accent: "#ff5722",
    initials: "AG",
    photo: asmitaPhoto,
    linkedin: "https://www.linkedin.com/in/asmita-gawde/",
  },
  {
    name: "Max Lebda",
    role: "Model Creator",
    area: "Hurricane Risk Model",
    accent: "#fbbf24",
    initials: "ML",
    photo: maxPhoto,
    linkedin: "https://www.linkedin.com/in/maxwell-lebda-001ba4178/",
  },
  {
    name: "Esha Ali",
    role: "Frontend Developer",
    area: "Frontend across all models",
    accent: "#9c27b0",
    initials: "EA",
    photo: eshaPhoto,
    linkedin: "https://www.linkedin.com/in/esha-sarfraz/",
  },
];

const About: React.FC = () => (
  <div className="about-page">
    <div className="about-hero">
      <p className="about-kicker">The Team</p>
      <h1>Built by people who care about climate risk.</h1>
      <p className="about-sub">
        UCInsure is a machine-learning platform that turns raw climate data into
        actionable insurance risk scores for floods, hurricanes, and wildfires.
      </p>
    </div>

    <div className="team-grid">
      {TEAM.map((member) => (
        <article
          key={member.name}
          className="team-card"
          style={{ "--accent": member.accent } as React.CSSProperties}
        >
          <a
            className="team-avatar"
            href={member.linkedin}
            target="_blank"
            rel="noreferrer"
            aria-label={`${member.name} LinkedIn profile`}
          >
            <img src={member.photo} alt={`${member.name} profile`} />
          </a>
          <div className="team-info">
            <h3 className="team-name">{member.name}</h3>
            <span className="team-role">{member.role}</span>
            <p className="team-area">{member.area}</p>
          </div>
        </article>
      ))}
    </div>

    <div className="about-project">
      <h2>About the Project</h2>
      <p>
        UCInsure combines open government datasets — FEMA NFIP claims, FEMA
        National Risk Index, and CAL FIRE incident records — with ensemble
        machine-learning models to predict insurance risk at the record level.
        Results are visualised interactively on a US choropleth map and a
        geographic risk heatmap.
      </p>
    </div>
  </div>
);

export default About;
