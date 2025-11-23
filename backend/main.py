from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from backend.api import routes_events, routes_location, event_detection, routes_reports

app = FastAPI()

# --- Enable CORS for frontend ---
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Vite's frontend URL
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# --- Include backend routes ---
app.include_router(routes_events.router, prefix="/api/routes_events", tags=["events"])
app.include_router(routes_location.router, prefix="/api/routes_location", tags=["location"])
app.include_router(event_detection.router, prefix="/api/event_detection", tags=["event_detection"])
app.include_router(routes_reports.router, prefix="/api/routes_reports", tags=["reports"])

@app.get("/")
def root():
    return {"message": "SilverSync backend running"}
