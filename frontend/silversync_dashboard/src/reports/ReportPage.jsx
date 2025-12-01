import { useEffect, useState, useRef } from "react";
import { useParams } from "react-router-dom";
import MobilityMap from "../components/MobilityMap";
import html2canvas from "html2canvas";

function formatTimestamp(ts) {
  const d = new Date(ts);
  const pad = (n) => String(n).padStart(2, "0");
  return `${d.getFullYear()}-${pad(d.getMonth() + 1)}-${pad(d.getDate())} `
       + `${pad(d.getHours())}:${pad(d.getMinutes())}:${pad(d.getSeconds())}`;
}

export default function ReportPage() {
  const { userId } = useParams();
  const [report, setReport] = useState(null);

  const mapWrapperRef = useRef(null);
  const [snapshot, setSnapshot] = useState(null);

  // -------------------------------
  // FETCH REPORT
  // -------------------------------
  useEffect(() => {
    const fetchReport = async () => {
      const res = await fetch(`http://127.0.0.1:8000/api/routes_reports/${userId}`);
      const data = await res.json();
      setReport(data);
    };

    fetchReport();
    const interval = setInterval(fetchReport, 1000);
    return () => clearInterval(interval);
  }, [userId]);

  // -------------------------------
  // CAPTURE SNAPSHOT BEFORE PRINT
  // -------------------------------
  useEffect(() => {
    const handleBeforePrint = async () => {
      if (!mapWrapperRef.current) return;

      const liveMapDiv = mapWrapperRef.current.querySelector(".live-map");
      if (!liveMapDiv) return;

      const canvas = await html2canvas(liveMapDiv, {
        backgroundColor: "#ffffff",
        scale: 2,
      });

      setSnapshot(canvas.toDataURL("image/png"));
    };

    const handleAfterPrint = () => setSnapshot(null);

    window.addEventListener("beforeprint", handleBeforePrint);
    window.addEventListener("afterprint", handleAfterPrint);

    return () => {
      window.removeEventListener("beforeprint", handleBeforePrint);
      window.removeEventListener("afterprint", handleAfterPrint);
    };
  }, []);

  if (!report) return <p>Loading report...</p>;

  return (
    <div style={{ padding: "20px" }}>

      <h1>Interaction Report for {report.name}</h1>
      <h3>User ID: {report.user_id}</h3>

      <h2>Socialization Overview</h2>
      <p>Today: {report.socialization.today_hours} hours</p>
      <p>This Week: {report.socialization.week_hours} hours</p>
      <p>This Month: {report.socialization.month_hours} hours</p>

      {/* EVENTS */}
      <h2 style={{ marginTop: "30px" }}>Major Events (4+ participants)</h2>
      <table style={{ width: "80%", margin: "auto", borderCollapse: "collapse" }}>
        <thead>
          <tr style={{ background: "#eef1f5" }}>
            <th style={{ padding: "10px", border: "1px solid #ccc" }}>Event</th>
            <th style={{ padding: "10px", border: "1px solid #ccc" }}>Start Time</th>
            <th style={{ padding: "10px", border: "1px solid #ccc" }}>End Time</th>
            <th style={{ padding: "10px", border: "1px solid #ccc" }}>Participants</th>
          </tr>
        </thead>

        <tbody>
          {report.events.map((e, idx) => (
            <tr key={idx}>
              <td style={{ padding: "10px", border: "1px solid #ddd" }}>
                <b>{getEventName(e.event_id)}</b><br />
                <small style={{ color: "#666" }}>ID: {e.event_id}</small>
              </td>

              <td style={{ padding: "10px", border: "1px solid #ddd" }}>
                {formatTimestamp(e.start)}
              </td>

              <td style={{ padding: "10px", border: "1px solid #ddd" }}>
                {formatTimestamp(e.end)}
              </td>

              <td style={{ padding: "10px", border: "1px solid #ddd", textAlign: "center" }}>
                {e.participants} people
              </td>
            </tr>
          ))}
        </tbody>
      </table>

      {/* -------------------------------- */}
      {/* MOBILITY MAP                     */}
      {/* -------------------------------- */}
      <h2 style={{ marginTop: "40px" }}>Mobility Map</h2>

      <div
        ref={mapWrapperRef}
        className="heatmap-wrapper"
        style={{ width: "800px", margin: "0 auto", position: "relative" }}
      >
        {/* LIVE MAP (hidden only in print mode) */}
        <div className="live-map">
          <MobilityMap
            heatmap={report.mobility.heatmap}
            movement_path={report.mobility.movement_path}
            events={report.events}
          />
        </div>

        {/* SNAPSHOT FOR PRINT */}
        {snapshot && (
          <img
            src={snapshot}
            alt="Mobility Map Snapshot"
            className="print-map-image"
            style={{width: "100%"}}
          />
        )}
      </div>

      <h2 style={{ marginTop: "40px" }}>Top Friends</h2>
      <ul>
        {report.friends.map((f) => (
          <li key={f.user_id}>
            {f.name} — {(f.overlap_minutes / 60).toFixed(2)} hours together
          </li>
        ))}
      </ul>

    </div>
  );
}

// -------------------------------
// Event naming
// -------------------------------
function seededRandom(seed) {
  const x = Math.sin(seed) * 10000;
  return x - Math.floor(x);
}

const EVENT_NAMES = [
  "Bingo Night","Karaoke Hour","Card Game Circle","Domino Tournament",
  "Arts & Crafts","Chair Yoga","Movie Afternoon","Bible Study",
  "Coffee Social","Music Therapy","Trivia Challenge","Gardening Club",
  "Community Lunch","Puzzle Hour","Balloon Volleyball"
];

function getEventName(eventId) {
  return EVENT_NAMES[Math.floor(seededRandom(eventId) * EVENT_NAMES.length)];
}
