import os
from datetime import datetime, timezone
from fastapi import FastAPI, Header, HTTPException
from pydantic import BaseModel

app = FastAPI(title="Aura Control Plane", version="0.1.0")
latest = {}

class Heartbeat(BaseModel):
    device_id: str
    training_status: str
    step: int
    loss: float | None = None
    model_parameters: int
    runtime_version: str

def authorize(value):
    expected = os.environ.get("AURA_CONTROL_TOKEN")
    if not expected or value != "Bearer " + expected:
        raise HTTPException(401, "Unauthorized")

@app.get("/health")
def health():
    return {"ok": True, "service": "aura-control-plane", "inference": "not-hosted"}

@app.post("/agent/heartbeat")
def heartbeat(body: Heartbeat, authorization: str | None = Header(default=None)):
    authorize(authorization)
    latest[body.device_id] = {**body.model_dump(), "received_at": datetime.now(timezone.utc).isoformat()}
    return {"accepted": True}

@app.get("/agent/{device_id}")
def get_agent(device_id: str, authorization: str | None = Header(default=None)):
    authorize(authorization)
    if device_id not in latest:
        raise HTTPException(404, "Device not registered.")
    return latest[device_id]
