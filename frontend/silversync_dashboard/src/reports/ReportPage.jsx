import { useEffect, useState } from "react";
import { useParams } from "react-router-dom";
import MobilityMap from "../components/MobilityMap";


export default function ReportPage() {
  const { userId } = useParams();
  const [report, setReport] = useState(null);

  useEffect(() => {
    const fetchReport = async () => {
      const res = await fetch(`http://127.0.0.1:8000/api/routes_reports/${userId}`);
      const data = await res.json();
      setReport(data);
    };

    fetchReport();
  }, [userId]);

  if (!report) return <p>Loading report...</p>;

  return (
    <div style={{ padding: "20px" }}>
      <h1>Interaction Report for {report.name}</h1>
      <h3>User ID: {report.user_id}</h3>

      <h2>Socialization Overview</h2>
      <p>Today: {report.socialization.today_hours} hours</p>
      <p>This Week: {report.socialization.week_hours} hours</p>
      <p>This Month: {report.socialization.month_hours} hours</p>

      <h2>Major Events (4+ participants)</h2>
      <ul>
        {report.events.map((e) => (
          <li key={e.event_id}>
            <b>Event {e.event_id}</b> — {e.start} → {e.end}  
            &nbsp;({e.participants} people)
          </li>
        ))}
      </ul>

      <h2>Mobility Map</h2>
      <MobilityMap 
        heatmap={report.mobility.heatmap}
        movement_path={report.mobility.movement_path}
        events={report.events}
      />

      <h2>Top Friends</h2>
      <ul>
        {report.friends.map((f) => (
          <li key={f.user_id}>
            {f.name} — {f.overlap_minutes} minutes together
          </li>
        ))}
      </ul>
    </div>
  );
}
