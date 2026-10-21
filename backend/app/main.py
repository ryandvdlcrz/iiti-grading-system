from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.config import settings
from app.routes import sections, admin, notifications, me, deadlines, termgrades, termgrades_csv, grade_components, view_grades, auth

import traceback
from fastapi import Request
from fastapi.responses import JSONResponse

app = FastAPI(title="Grading System API")

@app.exception_handler(Exception)
async def debug_unhandled(request: Request, exc: Exception):
    print("UNHANDLED:", request.url.path, traceback.format_exc(), flush=True)
    return JSONResponse(status_code=500, content={"detail": f"{type(exc).__name__}: {exc}"})

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