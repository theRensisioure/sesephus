import asyncio
import nats
import json
import time

async def main():
    # Connect to NATS
    nc = await nats.connect("localhost")
    
    # Mock Agent Update
    agent_data = {
        "name": "RECRUITER_AGENT",
        "node": "NODE_01",
        "status": "Busy",
        "current_task": "Analyzing VRAM usage on MSI MEG Vision",
        "resource_load": 0.85
    }
    
    await nc.publish("aether.monitoring.agent_status", json.dumps(agent_data).encode())
    print("[MOCK] Published agent status update.")
    
    # Mock Task Update
    task_data = {
        "domain": "RECRUITER",
        "status": "RUNNING",
        "payload_summary": "Scanning local vector store for matching roles."
    }
    await nc.publish("aether.monitoring.task_update", json.dumps(task_data).encode())
    print("[MOCK] Published task update.")
    
    await nc.close()

if __name__ == "__main__":
    asyncio.run(main())
