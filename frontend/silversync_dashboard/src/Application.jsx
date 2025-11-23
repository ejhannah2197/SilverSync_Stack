import { useEffect, useState } from "react";
import "./App_style.css";

export default function App() {
  const [activeTab, setActiveTab] = useState("overview");

  // User Data Tab
  const [userName, setUserName] = useState("");
  const [userData, setUserData] = useState(null);

  // Low Interaction
  const [lowUsers, setLowUsers] = useState([]);
  const [threshold, setThreshold] = useState(5);

  // Reports
  const [allUsers, setAllUsers] = useState([]);
  const [reportUserId, setReportUserId] = useState(null);

  // Overview Data
  const [activeDevices, setActiveDevices] = useState(0);
  const [eventsToday, setEventsToday] = useState(0);
  const [systemStatus, setSystemStatus] = useState("offline");

  const backendUrl = "http://127.0.0.1:8000/api/routes_events";

  // --------------------------------------------------------------------
  // Run Event Detection
  // --------------------------------------------------------------------
  const runEventDetection = async () => {
    try {
      const res = await fetch(
        "http://127.0.0.1:8000/api/event_detection/run-event-detection",
        { method: "POST", headers: { "Content-Type": "application/json" } }
      );

      const data = await res.json();
      alert(data.message || "Event detection started!");
    } catch (err) {
      console.error("Error running event detection:", err);
      alert("Failed to start event detection.");
    }
  };

  // --------------------------------------------------------------------
  // Load Low Interaction Users
  // --------------------------------------------------------------------
  useEffect(() => {
    const fetchLowUsers = async () => {
      try {
        const res = await fetch(
          `${backendUrl}/low-interaction?threshold_minutes=${threshold}`
        );
        const data = await res.json();
        setLowUsers(data);
      } catch (err) {
        console.error("Error fetching low users:", err);
      }
    };

    if (activeTab === "overview") {
      fetchLowUsers();
      const interval = setInterval(fetchLowUsers, 5000);
      return () => clearInterval(interval);
    }
  }, [threshold, activeTab]);

  // --------------------------------------------------------------------
  // User Search
  // --------------------------------------------------------------------
  const fetchUserData = async () => {
    if (!userName) return;

    try {
      const idRes = await fetch(
        `${backendUrl}/lookup_user_id?name=${encodeURIComponent(userName)}`
      );
      const idData = await idRes.json();

      if (!idData.user_id) {
        alert("User not found!");
        return;
      }

      const res = await fetch(`${backendUrl}/users?user_id=${idData.user_id}`);
      const data = await res.json();

      setUserData(data);
    } catch (err) {
      console.error("Error fetching user data:", err);
      alert("Failed to fetch user data.");
    }
  };

  // --------------------------------------------------------------------
  // Load All Users for Reports Tab
  // --------------------------------------------------------------------
  useEffect(() => {
    const fetchUsers = async () => {
      try {
        const res = await fetch("http://127.0.0.1:8000/api/routes_events/all-users");
        const data = await res.json();
        setAllUsers(data);
      } catch (err) {
        console.error("Failed to load users:", err);
      }
    };

    fetchUsers();
  }, []);

  // --------------------------------------------------------------------
  // Overview Cards
  // --------------------------------------------------------------------
  useEffect(() => {
    const fetchOverviewData = async () => {
      try {
        const resDevices = await fetch(`${backendUrl}/active-devices`);
        const dataDevices = await resDevices.json();
        setActiveDevices(dataDevices.active_devices ?? 0);

        const resEvents = await fetch(`${backendUrl}/events-today`);
        const dataEvents = await resEvents.json();
        setEventsToday(dataEvents.events_today ?? 0);

        const resStatus = await fetch(`${backendUrl}/system-status`);
        const dataStatus = await resStatus.json();
        setSystemStatus(dataStatus.status === "online" ? "online" : "offline");
      } catch (err) {
        console.error("Error fetching overview data:", err);
        setSystemStatus("offline");
      }
    };

    fetchOverviewData();
    const interval = setInterval(fetchOverviewData, 10000);
    return () => clearInterval(interval);
  }, []);

  // --------------------------------------------------------------------
  // Generate Report Button
  // --------------------------------------------------------------------
  const generateReport = () => {
    if (!reportUserId) {
      alert("Please select a user first.");
      return;
    }

    window.open(`/report/${reportUserId}`, "_blank");
  };

  // --------------------------------------------------------------------
  // RENDER UI
  // --------------------------------------------------------------------

  return (
    <div className="page">
      <header className="navbar navbar-expand-md navbar-light bg-light">
        <div className="container-xl">

          <a href="#" className="navbar-brand">
            <span className="navbar-brand-text">SilverSync Dashboard</span>
          </a>

          <button
            onClick={runEventDetection}
            className="btn btn p-0"
            style={{
              border: "none",
              background: "transparent",
              marginLeft: "370px",
              cursor: "pointer",
            }}
          >
            <img
              src="/SilverSyncLogo.png"
              alt="Run Event Detection"
              style={{ width: "60px", height: "60px" }}
            />
          </button>

          {/* NAVIGATION TABS */}
          <ul className="navbar-nav ms-auto">
            <li className="nav-item" onClick={() => setActiveTab("overview")}>
              <a className={`nav-link ${activeTab === "overview" ? "active" : ""}`}>
                Overview
              </a>
            </li>
            <li className="nav-item" onClick={() => setActiveTab("user")}>
              <a className={`nav-link ${activeTab === "user" ? "active" : ""}`}>
                User Data
              </a>
            </li>
            <li className="nav-item" onClick={() => setActiveTab("reports")}>
              <a className={`nav-link ${activeTab === "reports" ? "active" : ""}`}>
                Reports
              </a>
            </li>
          </ul>

        </div>
      </header>

      <div className="page-wrapper">
        <div className="container-xl mt-4">

          {/* ------------------------------------------------------------- */}
          {/*                         OVERVIEW TAB                          */}
          {/* ------------------------------------------------------------- */}
          {activeTab === "overview" && (
            <>
              <div className="row row-cards" style={{ position: "relative" }}></div>

              <div className="row row-cards">
                {/* Active Devices */}
                <div className="col-md-4">
                  <div className="card text-center">
                    <div className="card-body">
                      <h3 className="card-title">Active Devices</h3>
                      <p className="text-secondary">{activeDevices} Connected</p>
                    </div>
                  </div>
                </div>

                {/* Events Today */}
                <div className="col-md-4">
                  <div className="card text-center">
                    <div className="card-body">
                      <h3 className="card-title">Events Today</h3>
                      <p className="text-secondary">{eventsToday} Detected</p>
                    </div>
                  </div>
                </div>

                {/* System Status */}
                <div className="col-md-4">
                  <div className="card text-center">
                    <div className="card-body">
                      <h3 className="card-title">System Status</h3>
                      <span
                        className={`badge ${
                          systemStatus === "online" ? "bg-success" : "bg-danger"
                        }`}
                      >
                        {systemStatus.charAt(0).toUpperCase() + systemStatus.slice(1)}
                      </span>
                    </div>
                  </div>
                </div>
              </div>

              {/* Low Interaction */}
              <div className="card mt-4">
                <div className="card-body">
                  <h3>Low Interaction Users</h3>

                  <label>Time threshold (minutes):</label>
                  <input
                    type="number"
                    value={threshold}
                    onChange={(e) => setThreshold(parseInt(e.target.value) || 0)}
                    className="form-control mb-3"
                  />

                  <table className="table">
                    <thead>
                      <tr>
                        <th>User Name</th>
                        <th>Total Interaction (min)</th>
                      </tr>
                    </thead>
                    <tbody>
                      {lowUsers.map((u) => (
                        <tr key={u.user_id}>
                          <td>{u.name}</td>
                          <td>{u.total_minutes}</td>
                        </tr>
                      ))}
                    </tbody>
                  </table>

                </div>
              </div>
            </>
          )}

          {/* ------------------------------------------------------------- */}
          {/*                        USER DATA TAB                           */}
          {/* ------------------------------------------------------------- */}
          {activeTab === "user" && (
            <div className="card">
              <div className="card-body">

                <h3>User Search</h3>

                <input
                  type="text"
                  placeholder="Enter User Name"
                  value={userName}
                  onChange={(e) => setUserName(e.target.value)}
                  className="form-control mb-2"
                />

                <button onClick={fetchUserData} className="btn btn-primary">
                  Get Data
                </button>

                {userData && (
                  <div className="mt-3">
                    <h4>Total Interaction Time: {userData.total_interaction_minutes} min</h4>
                    <h5>Recent Interactions:</h5>

                    {userData.recent_interactions?.length > 0 ? (
                      <ul>
                        {userData.recent_interactions.map((r, i) => {
                          const start = new Date(r.start_time);
                          const end = new Date(r.end_time);
                          const durationMin = Math.round((end - start) / 60000);

                          const dateStr = start.toLocaleDateString("en-US", {
                            year: "numeric",
                            month: "long",
                            day: "2-digit",
                          });

                          const timeStr = end.toLocaleTimeString("en-US", {
                            hour: "2-digit",
                            minute: "2-digit",
                          });

                          return (
                            <li key={i}>
                              <b>{dateStr}</b> — {timeStr} — Duration: {durationMin} min —
                              Location: ({r.x_event}, {r.y_event})
                            </li>
                          );
                        })}
                      </ul>
                    ) : (
                      <p>No recent interactions found.</p>
                    )}
                  </div>
                )}

              </div>
            </div>
          )}

          {/* ------------------------------------------------------------- */}
          {/*                           REPORTS TAB                          */}
          {/* ------------------------------------------------------------- */}
          {activeTab === "reports" && (
            <div className="card">
              <div className="card-body">

                <h3>Generate Interaction Report</h3>

                {/* Dropdown */}
                <label>Select User:</label>
                <select
                  className="form-select mb-3"
                  value={reportUserId || ""}
                  onChange={(e) => setReportUserId(e.target.value)}
                >
                  <option value="">Select a user...</option>

                  {allUsers.map((u) => (
                    <option key={u.id} value={u.id}>
                      {u.name} (ID {u.id})
                    </option>
                  ))}
                </select>

                <button
                  className="btn btn-primary"
                  disabled={!reportUserId}
                  onClick={generateReport}
                >
                  Generate Interaction Report
                </button>

                <div className="mt-4">
                  <h4>Report Output</h4>
                  <p>Select a user and click “Generate Interaction Report”.</p>
                </div>

              </div>
            </div>
          )}

        </div>
      </div>
    </div>
  );
}
