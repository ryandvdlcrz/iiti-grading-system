from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.config import settings
from app.routes import sections, admin, notifications, me, deadlines, termgrades, termgrades_csv, grade_components, view_grades, auth

app = FastAPI(title="Grading System API")

# Allows the React dev server (localhost:5173 by default) to call this API.
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
    expose_headers=["Content-Disposition"],  # needed for the CSV download filename
)

app.include_router(auth.router)
app.include_router(sections.router)
app.include_router(admin.router)
app.include_router(notifications.router)
app.include_router(me.router)
app.include_router(deadlines.router)
app.include_router(termgrades.router)
app.include_router(termgrades_csv.router)
app.include_router(grade_components.router)
app.include_router(view_grades.router)

@app.get("/health")
def health_check():
    return {"status": "ok", "mock_mode": settings.USE_MOCK_DATA}