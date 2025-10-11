from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from backend.api.routes_events import router as events_router
from backend.api.routes_location import router as location_router

app = FastAPI(title="SilverSync API")

# Enable CORS for your frontend
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include API routers
app.include_router(events_router)
app.include_router(location_router)

@app.get("/")
def root():
    return {"message": "SilverSync backend running"}
