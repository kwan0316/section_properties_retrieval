from fastapi.middleware.cors import CORSMiddleware
from fastapi import FastAPI
from uc_ub_data_retrieval import create_fastapi_app

# Create app using factory from the main module so tables load at startup
app = create_fastapi_app()

# Add simple CORS (optional, safe defaults)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/healthz")
async def healthz():
    return {"status": "ok"}
