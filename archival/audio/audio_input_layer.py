import asyncio
import nats
import json
import time
import sounddevice as sd
import numpy as np
import sqlite3
from typing import Optional
from pydantic import BaseModel

# --- Database Setup (SQLCipher would be used here) ---
DB_PATH = "data/devices.db"

def init_db():
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS audio_devices (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            channels INTEGER,
            sample_rate REAL,
            is_active INTEGER DEFAULT 0
        )
    """)
    conn.commit()
    conn.close()

# --- Models ---
class AudioStatus(BaseModel):
    name: str = "AUDIO_INPUT_LAYER"
    node: str = "NODE_01"
    status: str = "Idle"
    current_task: Optional[str] = None
    resource_load: float = 0.0
    db_level: float = 0.0

# --- Audio Capture ---
class AudioLayer:
    def __init__(self, nats_client):
        self.nc = nats_client
        self.running = True
        self.current_db = -100.0

    async def broadcast_status(self):
        while self.running:
            status = AudioStatus(
                status="Active" if self.running else "Idle",
                current_task="Capturing System Audio",
                resource_load=0.1,
                db_level=self.current_db
            )
            await self.nc.publish("aether.monitoring.agent_status", json.dumps(status.dict()).encode())
            await asyncio.sleep(2)

    def audio_callback(self, indata, frames, time, status):
        if status:
            print(f"Audio Error: {status}")
        # Calculate simple RMS/dB level
        rms = np.sqrt(np.mean(indata**2))
        self.current_db = 20 * np.log10(rms) if rms > 0 else -100.0

    async def run(self):
        # Start broadcast task
        asyncio.create_task(self.broadcast_status())
        
        # Start audio stream
        with sd.InputStream(callback=self.audio_callback):
            while self.running:
                await asyncio.sleep(1)

async def main():
    # Ensure data dir exists
    import os
    if not os.path.exists("data"):
        os.makedirs("data")
    
    init_db()
    
    try:
        nc = await nats.connect("localhost")
        print("[AUDIO] Connected to NATS")
        
        layer = AudioLayer(nc)
        await layer.run()
    except Exception as e:
        print(f"[AUDIO] Failed: {e}")

if __name__ == "__main__":
    asyncio.run(main())
