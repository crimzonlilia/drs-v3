"""
Main FastAPI server initialization. Mounts modular routers and configures CORS.
"""

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from server.routers import projects, translation, memory, auth, docs
from core.utils.db import init_db

app = FastAPI(
    title="DRS v3 REST API",
    description="Backend API services for DRS v3 Translation Workspace",
    version="3.0.0"
)

@app.on_event("startup")
async def startup_event():
    await init_db()


# Enable CORS for Next.js frontend (default port 3000)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Adjust in production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include Routers
app.include_router(auth.router)
app.include_router(projects.router)
app.include_router(translation.router)
app.include_router(memory.router)
app.include_router(docs.router)
