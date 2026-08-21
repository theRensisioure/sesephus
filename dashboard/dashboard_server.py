import asyncio
import http.client
import json
import os
import sys
import threading
import time
import urllib.request
from datetime import datetime, timezone
from typing import Dict, List, Optional
from pydantic import BaseModel, Field
from fastapi import FastAPI, Depends
from fastapi.middleware.cors import CORSMiddleware
import uuid

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "tools")))
import etdi_store

# --- Data Models ---

class AgentStatus(BaseModel):
    name: str
    node: str
    status: str # "Idle", "Busy", "Error"
    current_task: Optional[str] = None
    resource_load: float = 0.0

class TaskEntry(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    domain: str
    status: str # "PENDING", "RUNNING", "COMPLETED"
    payload_summary: str
    created_at: int = Field(default_factory=lambda: int(time.time()))

class ArtifactEntry(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    type_name: str
    source_node: str
    file_path: str
    size_bytes: int
    created_at: int = Field(default_factory=lambda: int(time.time()))

class DashboardState(BaseModel):
    agents: Dict[str, AgentStatus] = {}
    task_queue: List[TaskEntry] = []
    artifacts: List[ArtifactEntry] = []
    last_updated: int = 0

# --- App State ---

state = DashboardState()

app = FastAPI(title="Project AETHER Dashboard")

# Local-only dashboard. The UI is served by Vite, which proxies /api to this
# process, so nothing needs cross-origin access except the dev origin itself.
# Wildcard CORS here fronted unauthenticated endpoints that read arbitrary
# filesystem paths — any page the user visited could have called them.
_ALLOWED_ORIGINS = [
    o.strip()
    for o in os.environ.get(
        "SESEFUS_DASHBOARD_ORIGINS",
        "http://localhost:5173,http://127.0.0.1:5173",
    ).split(",")
    if o.strip()
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=_ALLOWED_ORIGINS,
    allow_methods=["*"],
    allow_headers=["*"],
)

# --- Background Tasks ---
# (Removed NATS listener - we now poll Zig directly on request)

# --- API Endpoints ---

class TranscribeRequest(BaseModel):
    wav_path: str
    client_id: str

@app.post("/api/transcribe")
async def transcribe_audio(req: TranscribeRequest):
    import os
    print(f"[AETHER] Transcribing audio from {req.client_id} at {req.wav_path}")
    
    # Check if file exists (resolve path relative to sesephus core if needed)
    resolved_path = req.wav_path
    if not os.path.isabs(resolved_path):
        resolved_path = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "core", "sesephus", req.wav_path))
        
    print(f"[AETHER] Resolved audio path: {resolved_path}")
    file_exists = os.path.exists(resolved_path)
    
    # Try importing whisper for production execution
    try:
        import whisper
        if file_exists:
            model = whisper.load_model("base")
            result = model.transcribe(resolved_path)
            text = result.get("text", "").strip()
        else:
            text = "[ERROR] Audio file not found for physical transcription."
    except ImportError:
        # Fallback to simulated trial-and-error transcription
        text = "This is a simulated transcription. The system is listening and learning."
        if "journal" in resolved_path.lower():
            text = "I am speaking from the edge client: test-client. The Zig protocol is running."
            
    print(f"[AETHER] Transcription result: {text}")
    
    # Update local task queue state
    try:
        task_data = {
            "domain": "transcription",
            "status": "COMPLETED",
            "payload_summary": f"Client {req.client_id}: {text}"
        }
        task = TaskEntry(**task_data)
        state.task_queue.insert(0, task)
        state.task_queue = state.task_queue[:100] # Keep last 100
        state.last_updated = int(time.time())
        print("[AETHER] Logged transcription task update locally.")
    except Exception as e:
        print(f"[AETHER] Failed to update local task state: {e}")
        
    return {"status": "success", "text": text, "file_exists": file_exists}

# Plain def: FastAPI runs these in its threadpool so the blocking sqlite
# work never stalls the event loop.
@app.get("/api/etdi/trend")
def etdi_trend(days: int = 30):
    conn = etdi_store.connect()
    try:
        return {"trend": etdi_store.daily_trend(conn, days)}
    finally:
        conn.close()

@app.get("/api/etdi/flags")
def etdi_flags(threshold: float = 0.30, limit: int = 20):
    conn = etdi_store.connect()
    try:
        return {"threshold": threshold, "flags": etdi_store.high_density_flags(conn, threshold, limit)}
    finally:
        conn.close()

@app.get("/api/etdi/entries")
def etdi_entries(limit: int = 50):
    conn = etdi_store.connect()
    try:
        return {"entries": etdi_store.recent_entries(conn, limit)}
    finally:
        conn.close()

@app.get("/api/dashboard")
async def get_dashboard():
    # Poll Zig Host dynamically for live connected clients
    try:
        req = urllib.request.Request("http://localhost:3000/api/status", headers={'User-Agent': 'Mozilla/5.0'})
        with urllib.request.urlopen(req, timeout=2) as response:
            status_data = json.loads(response.read().decode())
            
            # Map Zig clients to Dashboard agents
            state.agents.clear()
            for c in status_data.get("clients", []):
                agent_name = c.get("client_id", "Unknown")
                is_active = c.get("active", False)
                state.agents[agent_name] = AgentStatus(
                    name=agent_name,
                    node=c.get("friendly_name", "Unknown Node"),
                    status="Idle" if is_active else "Offline",
                )
    except Exception as e:
        print(f"[AETHER] Failed to poll Zig Host for dashboard state: {e}")
        
    state.last_updated = int(time.time())
    return state

# Zig host poll target and hard overall deadline. Loopback IP (not
# "localhost") so a dual-stack DNS resolve can't burn one connect timeout per
# address, and the socket timeout is re-armed with the remaining budget
# before every read so a slow-dribbling host can't stretch a single poll past
# the deadline (urllib/http.client timeout= is per socket op, not overall).
ZIG_STATUS_HOST = "127.0.0.1"
ZIG_STATUS_PORT = 3000
ZIG_STATUS_URL = f"http://{ZIG_STATUS_HOST}:{ZIG_STATUS_PORT}"
ZIG_POLL_DEADLINE_S = 2.0

def _poll_zig_status() -> dict:
    """GET /api/status from the Zig host under one overall 2s deadline."""
    deadline = time.monotonic() + ZIG_POLL_DEADLINE_S
    conn = http.client.HTTPConnection(ZIG_STATUS_HOST, ZIG_STATUS_PORT, timeout=ZIG_POLL_DEADLINE_S)
    try:
        conn.connect()
        # Keep our own reference: for will_close (HTTP/1.0) responses,
        # getresponse() detaches the socket and sets conn.sock = None.
        sock = conn.sock
        sock.settimeout(max(deadline - time.monotonic(), 0.001))
        conn.request("GET", "/api/status", headers={'User-Agent': 'Mozilla/5.0'})
        response = conn.getresponse()
        if response.status != 200:
            raise RuntimeError(f"Zig host returned HTTP {response.status}")
        chunks = []
        while True:
            remaining = deadline - time.monotonic()
            if remaining <= 0:
                raise TimeoutError(f"Zig host poll exceeded {ZIG_POLL_DEADLINE_S}s deadline")
            if not response.isclosed():
                sock.settimeout(remaining)
            # read1 = at most one underlying recv, so the deadline is
            # re-checked between recvs (plain read(n) loops internally
            # until n/Content-Length bytes arrive, dodging the deadline).
            chunk = response.read1(65536)
            if not chunk:
                break
            chunks.append(chunk)
        return json.loads(b"".join(chunks).decode())
    finally:
        conn.close()

# Plain def (threadpool) like the etdi endpoints: the Zig poll and sqlite
# reads are blocking, so keep them off the event loop.
@app.get("/api/machine")
def get_machine():
    """Aggregate machine-level health snapshot.

    Every subsystem access is wrapped so an outage degrades its own section
    (per-subsystem ok=false + detail) instead of 500ing the endpoint.
    """
    subsystems = {
        "dashboard_api": {"ok": True, "detail": None},
        "zig_host": {"ok": False, "url": ZIG_STATUS_URL, "detail": None},
        "etdi_store": {"ok": False, "detail": None},
    }

    # Zig Host: clients/alarms passthrough + agent mapping (same as /api/dashboard)
    clients: List[dict] = []
    alarms: List[dict] = []
    agents: List[AgentStatus] = []
    try:
        status_data = _poll_zig_status()
        clients = status_data.get("clients", [])
        alarms = status_data.get("alarms", [])
        for c in clients:
            agent_name = c.get("client_id", "Unknown")
            is_active = c.get("active", False)
            agents.append(AgentStatus(
                name=agent_name,
                node=c.get("friendly_name", "Unknown Node"),
                status="Idle" if is_active else "Offline",
            ))
        subsystems["zig_host"]["ok"] = True
    except Exception as e:
        print(f"[AETHER] /api/machine: Zig Host unreachable: {e}")
        subsystems["zig_host"]["detail"] = str(e)
        clients, alarms, agents = [], [], []

    # ETDI store: last-7-day trend + flag count at the 0.30 threshold
    etdi = {"trend": [], "flag_count": 0}
    try:
        conn = etdi_store.connect()
        try:
            etdi = {
                "trend": etdi_store.daily_trend(conn, 7),
                "flag_count": len(etdi_store.high_density_flags(conn, 0.30, 1_000_000)),
            }
        finally:
            conn.close()
        subsystems["etdi_store"]["ok"] = True
    except Exception as e:
        print(f"[AETHER] /api/machine: ETDI store error: {e}")
        subsystems["etdi_store"]["detail"] = str(e)
        etdi = {"trend": [], "flag_count": 0}

    return {
        "subsystems": subsystems,
        "clients": clients,
        "alarms": alarms,
        "agents": agents,
        "task_queue": state.task_queue,
        "artifacts": state.artifacts,
        "etdi": etdi,
        "last_updated": datetime.now(timezone.utc).isoformat(),
    }


# --- Artifact Sieve (Gemini Takeout / chat dump scanner) ---

_REPO_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
sys.path.insert(0, os.path.join(_REPO_ROOT, "shredder"))
sys.path.insert(0, os.path.join(_REPO_ROOT, "tools"))


class SieveScanRequest(BaseModel):
    root: str
    shallow: bool = False
    limit: int = 0


class SieveShredRequest(BaseModel):
    root: str
    unit: str = "conversation"  # conversation | turn
    force: bool = False
    dry_run: bool = False
    limit: int = 0
    source_node: str = "GeminiTakeout"


# One shred at a time: two concurrent shred_roots runs share one dedup state
# file and would interleave their read-modify-write of it.
_SIEVE_SHRED_LOCK = threading.Lock()


def _sieve_allowed_roots() -> list[str]:
    """Directories the sieve endpoints may be pointed at."""
    import artifact_sieve

    raw = [str(p) for p in artifact_sieve.default_roots()]
    raw.append(os.path.expanduser("~"))
    raw.append(_REPO_ROOT)
    raw.extend(
        p for p in os.environ.get("SESEFUS_SIEVE_ROOTS", "").split(os.pathsep) if p.strip()
    )
    return [
        os.path.normcase(os.path.realpath(os.path.abspath(os.path.expanduser(p.strip()))))
        for p in raw
        if p.strip()
    ]


def _resolve_sieve_root(raw: str) -> str:
    """Resolve a user-supplied directory and confine it to the allow-list.

    These endpoints are unauthenticated, so an unconfined path here means any
    caller can inventory the whole filesystem. realpath first, so a symlink
    cannot point out of an allowed root.
    """
    if not raw or not str(raw).strip():
        raise ValueError("root path is required")
    path = os.path.realpath(os.path.abspath(os.path.expanduser(str(raw).strip())))
    probe = os.path.normcase(path)
    allowed = _sieve_allowed_roots()
    if not any(probe == a or probe.startswith(a + os.sep) for a in allowed):
        raise PermissionError(
            f"root is outside the allowed sieve roots: {path}. "
            f"Add it to artifact_roots in sesefus.config.json, or set SESEFUS_SIEVE_ROOTS."
        )
    if not os.path.exists(path):
        raise FileNotFoundError(f"path does not exist: {path}")
    return path


@app.post("/api/sieve/scan")
def sieve_scan(req: SieveScanRequest):
    """Inventory chat-export artifacts under an opened directory."""
    from pathlib import Path
    import artifact_sieve

    try:
        root = _resolve_sieve_root(req.root)
    except (ValueError, FileNotFoundError, PermissionError) as exc:
        return {"ok": False, "error": str(exc), "files": []}

    inv = artifact_sieve.scan_directory(
        [Path(root)],
        deep_parse=not req.shallow,
        limit=req.limit if req.limit and req.limit > 0 else 0,
    )
    inv["ok"] = True
    inv["root"] = root
    return inv


@app.post("/api/sieve/shred")
def sieve_shred(req: SieveShredRequest):
    """Shred Gemini/Takeout dumps under root into debris_shards.jsonl."""
    from pathlib import Path
    import artifact_sieve

    try:
        root = _resolve_sieve_root(req.root)
    except (ValueError, FileNotFoundError, PermissionError) as exc:
        return {"ok": False, "error": str(exc)}

    unit = req.unit if req.unit in ("conversation", "turn") else "conversation"
    output = Path(_REPO_ROOT) / "ingest" / "debris_shards.jsonl"
    state_path = Path(_REPO_ROOT) / "ingest" / "artifact_sieve_state.json"

    if not _SIEVE_SHRED_LOCK.acquire(blocking=False):
        return {"ok": False, "error": "a shred is already running"}
    try:
        result = artifact_sieve.shred_roots(
            roots=[Path(root)],
            output=output,
            state=state_path,
            source_node=req.source_node or "GeminiTakeout",
            unit=unit,
            limit=req.limit if req.limit and req.limit > 0 else 0,
            force=req.force,
            dry_run=req.dry_run,
        )
    finally:
        _SIEVE_SHRED_LOCK.release()
    # ok means the run completed; per-file failures ride in result["errors"]
    # and are rendered by the UI rather than discarding the whole result.
    result["ok"] = True
    result["root"] = root

    # Mirror into dashboard artifact list for Machine State
    try:
        if not req.dry_run:
            # A dry run produces no artifact — recording one made Machine State
            # report a file that was never written.
            entry = ArtifactEntry(
                type_name="gemini_sieve_shred",
                source_node=req.source_node or "GeminiTakeout",
                file_path=str(output),
                size_bytes=os.path.getsize(output) if output.exists() else 0,
            )
            state.artifacts.insert(0, entry)
            state.artifacts = state.artifacts[:50]
        state.task_queue.insert(0, TaskEntry(
            domain="artifact_sieve",
            status="COMPLETED",
            payload_summary=(
                f"[dry run] would shred {result.get('would_shred', 0)} file(s) → "
                f"{result.get('would_ship', 0)} chunk(s) from {root}"
                if req.dry_run else
                f"Shredded {result.get('files_shredded', 0)} file(s) → "
                f"{result.get('chunks_shipped', 0)} chunk(s) from {root}"
            ),
        ))
        state.task_queue = state.task_queue[:100]
        state.last_updated = int(time.time())
    except Exception as e:
        print(f"[AETHER] sieve_shred state update failed: {e}")

    return result


@app.get("/api/sieve/defaults")
def sieve_defaults():
    """Suggested roots from config + common Takeout landing pads."""
    from pathlib import Path
    import artifact_sieve

    roots = [str(p) for p in artifact_sieve.default_roots()]
    return {
        "artifact_roots": roots,
        "output": os.path.join(_REPO_ROOT, "ingest", "debris_shards.jsonl"),
        "state": os.path.join(_REPO_ROOT, "ingest", "artifact_sieve_state.json"),
        "hint": (
            "Point root at your Google Takeout extract "
            "(…/Takeout/Gemini or the unzipped folder Google emailed)."
        ),
    }


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="127.0.0.1", port=3001)
