import { useEffect, useState } from "react";
import "./App_style.css";

export default function App() {
  const [activeTab, setActiveTab] = useState("overview");
  const [userName, setUserName] = useState("");
  const [userData, setUserData] = useState(null);
  const [lowUsers, setLowUsers] = useState([]);
  const [threshold, setThreshold] = useState(5);

  const backendUrl = "http://127.0.0.1:8000/api/routes_events";

  // Fetch low interaction users periodically
  useEffect(() => {
    if (activeTab === "low") {
      const fetchLowUsers = async () => {
        try {
          const res = await fetch(`${backendUrl}/low-interaction?threshold_minutes=${threshold}`);
          const data = await res.json();
          setLowUsers(data);
        } catch (err) {
          console.error("Error fetching low users:", err);
        }
      };
      fetchLowUsers();
      const interval = setInterval(fetchLowUsers, 5000);
      return () => clearInterval(interval);
    }
  }, [threshold, activeTab]);


  // Fetch selected user data by name
  const fetchUserData = async () => {
    if (!userName) return;
    try {
      // Step 1: Get user ID from name
      const idRes = await fetch(`${backendUrl}/lookup_user_id?name=${encodeURIComponent(userName)}`);
      const idData = await idRes.json();

      if (!idData.user_id) {
        alert("User not found!");
        return;
      }

      // Step 2: Use the found ID to get data
      const res = await fetch(`${backendUrl}/users?user_id=${idData.user_id}`);
      const data = await res.json();

      console.log("Fetched user data:", data);
      setUserData(data);
    } catch (err) {
      console.error("Error fetching user data:", err);
      alert("Failed to fetch user data.");
    }
  };



  return (
    <div className="page">
      <header className="navbar navbar-expand-md navbar-light bg-light">
        <div className="container-xl">
          <a href="#" className="navbar-brand">
            <span className="navbar-brand-text">SilverSync Dashboard</span>
          </a>

          <ul className="navbar-nav ms-auto">
            <li className="nav-item" onClick={() => setActiveTab("overview")}>
              <a className={`nav-link ${activeTab === "overview" ? "active" : ""}`}>Overview</a>
            </li>
            <li className="nav-item" onClick={() => setActiveTab("user")}>
              <a className={`nav-link ${activeTab === "user" ? "active" : ""}`}>User Data</a>
            </li>
            <li className="nav-item" onClick={() => setActiveTab("low")}>
              <a className={`nav-link ${activeTab === "low" ? "active" : ""}`}>Low Interaction</a>
            </li>
          </ul>
        </div>
      </header>

      <div className="page-wrapper">
        <div className="container-xl mt-4">
          {/* Overview Tab */}
          {activeTab === "overview" && (
            <div className="row row-cards">
              <div className="col-md-4">
                <div className="card">
                  <div className="card-body text-center">
                    <h3 className="card-title">Active Devices</h3>
                    <p className="text-secondary">32 Connected</p>
                  </div>
                </div>
              </div>
              <div className="col-md-4">
                <div className="card">
                  <div className="card-body text-center">
                    <h3 className="card-title">Events Today</h3>
                    <p className="text-secondary">128 Detected</p>
                  </div>
                </div>
              </div>
              <div className="col-md-4">
                <div className="card">
                  <div className="card-body text-center">
                    <h3 className="card-title">System Status</h3>
                    <span className="badge bg-success">Online</span>
                  </div>
                </div>
              </div>
            </div>
          )}

          {/* User Data Tab */}
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
                    <h4>Total Interaction Time: {userData.total_interaction_minutes ?? 0} min</h4>
                    <h5>Recent Interactions:</h5>
                    {userData.recent_interactions && userData.recent_interactions.length > 0 ? (
                      <ul>
                        {userData.recent_interactions.map((r, i) => {
                          const start = new Date(r.start_time);
                          const end = new Date(r.end_time);
                          const durationMin = Math.round((end - start) / 60000);

                          const dateStr = start.toLocaleDateString("en-US", {
                            year: "numeric",
                            month: "long",
                            day: "2-digit"
                          });
                          const timeStr = end.toLocaleTimeString("en-US", {
                            hour: "2-digit",
                            minute: "2-digit"
                          });

                          return (
                            <li key={i}>
                              <b>{dateStr}</b> — {timeStr} — Duration: {durationMin} min — Location: {r.location}
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

          {/* Low Interaction Users Tab */}
          {activeTab === "low" && (
            <div className="card">
              <div className="card-body">
                <h3>Low Interaction Users</h3>
                <label>Time threshold (minutes):</label>
                <input
                  type="number"
                  value={threshold}
                  onChange={(e) => setThreshold(e.target.value)}
                  className="form-control mb-3"
                />
                <table className="table">
                  <thead>
                    <tr>
                      <th>User ID</th>
                      <th>Total Interaction (min)</th>
                    </tr>
                  </thead>
                  <tbody>
                    {lowUsers.map((u) => (
                      <tr key={u.user_id}>
                        <td>{u.user_id}</td>
                        <td>{u.total_minutes}</td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
