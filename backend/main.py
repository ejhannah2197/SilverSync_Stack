from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from backend.api import routes_events, routes_location 

app = FastAPI()

# --- Enable CORS for frontend ---
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173"],  # Vite's frontend URL
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# --- Include backend routes ---
app.include_router(routes_events.router, prefix="/api/routes_events", tags=["events"])
app.include_router(routes_location.router, prefix="/api/routes_location", tags=["location"])


@app.get("/")
def root():
    return {"message": "SilverSync backend running"}
