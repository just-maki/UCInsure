import React, { useEffect } from "react";
import { MapContainer, TileLayer, CircleMarker, Popup, Tooltip, useMap } from "react-leaflet";
import "leaflet/dist/leaflet.css";
import "./RiskMap.css";

export interface MapPoint {
  lat: number;
  lon: number;
  risk: number;
  label: string;
}

interface RiskMapProps {
  points?: MapPoint[];
  /** Shown in the empty-state overlay */
  emptyMessage?: string;
  /** Zoom to fit all points once they arrive */
  fitPoints?: boolean;
}

const RISK_COLOR: Record<string, string> = {
  high: "#ef4444",
  medium: "#f59e0b",
  low: "#22c55e",
};

/** Auto-fits the map viewport to the provided points. */
const FitBounds: React.FC<{ points: MapPoint[] }> = ({ points }) => {
  const map = useMap();
  useEffect(() => {
    if (points.length === 0) return;
    const lats = points.map((p) => p.lat);
    const lons = points.map((p) => p.lon);
    map.fitBounds(
      [
        [Math.min(...lats), Math.min(...lons)],
        [Math.max(...lats), Math.max(...lons)],
      ],
      { padding: [30, 30], maxZoom: 9 }
    );
  }, [points, map]);
  return null;
};

const RiskMap: React.FC<RiskMapProps> = ({
  points = [],
  emptyMessage = "Upload a dataset to see the risk map",
  fitPoints = true,
}) => {
  const hasData = points.length > 0;

  return (
    <div className="risk-map-wrapper">
      <MapContainer
        center={[39.5, -98.35]}
        zoom={4}
        className="risk-map-container"
        scrollWheelZoom={true}
      >
        <TileLayer
          url="https://{s}.basemaps.cartocdn.com/dark_all/{z}/{x}/{y}{r}.png"
          attribution='&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a> &copy; <a href="https://carto.com/">CARTO</a>'
        />

        {hasData && fitPoints && <FitBounds points={points} />}

        {points.map((pt, i) => (
          <CircleMarker
            key={i}
            center={[pt.lat, pt.lon]}
            radius={4}
            pathOptions={{
              fillColor: RISK_COLOR[pt.label] ?? "#888",
              color: RISK_COLOR[pt.label] ?? "#888",
              weight: 0.75,
              opacity: 0.78,
              fillOpacity: 0.76,
            }}
          >
            <Tooltip className="risk-tooltip" direction="top" opacity={1}>
              <strong>{pt.label.toUpperCase()} RISK</strong>
              <span>{(pt.risk * 10).toFixed(2)} / 10</span>
            </Tooltip>
            <Popup className="risk-popup">
              <strong>{pt.label.toUpperCase()} RISK</strong>
              <br />
              Score: {(pt.risk * 10).toFixed(2)} / 10
            </Popup>
          </CircleMarker>
        ))}
      </MapContainer>

      {!hasData && (
        <div className="map-empty-overlay">
          <span>{emptyMessage}</span>
        </div>
      )}

      {hasData && (
        <div className="map-legend">
          {(["low", "medium", "high"] as const).map((lvl) => (
            <span key={lvl} className="map-legend-item">
              <span
                className="map-legend-dot"
                style={{ background: RISK_COLOR[lvl] }}
              />
              {lvl.charAt(0).toUpperCase() + lvl.slice(1)}
            </span>
          ))}
          <span className="map-legend-count">{points.length.toLocaleString()} points</span>
        </div>
      )}
    </div>
  );
};

export default RiskMap;
