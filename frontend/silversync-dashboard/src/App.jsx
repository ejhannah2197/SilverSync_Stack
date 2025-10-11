export default function App() {
  return (
    <div className="page">
      <header className="navbar navbar-expand-md navbar-light bg-light">
        <div className="container-xl">
          <a href="#" className="navbar-brand">
            <span className="navbar-brand-text">SilverSync Dashboard</span>
          </a>
        </div>
      </header>

      <div className="page-wrapper">
        <div className="container-xl mt-4">
          <div className="row row-cards">
            <div className="col-md-6 col-lg-4">
              <div className="card">
                <div className="card-body text-center">
                  <h3 className="card-title">Active Devices</h3>
                  <p className="text-secondary">32 Connected</p>
                </div>
              </div>
            </div>
            <div className="col-md-6 col-lg-4">
              <div className="card">
                <div className="card-body text-center">
                  <h3 className="card-title">Events Today</h3>
                  <p className="text-secondary">128 Detected</p>
                </div>
              </div>
            </div>
            <div className="col-md-6 col-lg-4">
              <div className="card">
                <div className="card-body text-center">
                  <h3 className="card-title">System Status</h3>
                  <span className="badge bg-success">Online</span>
                </div>
              </div>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}
