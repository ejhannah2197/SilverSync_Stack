import React from "react";
import ReactDOM from "react-dom/client";
import App from "./Application.jsx";
import "@tabler/core/dist/css/tabler.min.css"; // ✅ Tabler styles
import "@tabler/core/dist/js/tabler.min.js";   // optional JS for interactivity

ReactDOM.createRoot(document.getElementById("root")).render(
  <React.StrictMode>
    <App />
  </React.StrictMode>
);


export const API_BASE_URL = "http://localhost:8000"