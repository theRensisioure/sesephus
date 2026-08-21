import asyncio
import nats
import json
import time
import random

async def simulate_agent(nc, name, node, role):
    while True:
        # Simulate work/idle cycle
        is_busy = random.random() > 0.3
        status = "Busy" if is_busy else "Idle"
        task = f"Processing {role} requests" if is_busy else None
        
        agent_data = {
            "name": name,
            "node": node,
            "status": status,
            "current_task": task,
            "resource_load": round(random.uniform(0.1, 0.9), 2)
        }
        await nc.publish("aether.monitoring.agent_status", json.dumps(agent_data).encode())
        
        if is_busy:
            task_data = {
                "domain": role,
                "status": "RUNNING",
                "payload_summary": f"Active session on {node} for {name}",
                "created_at": int(time.time())
            }
            await nc.publish("aether.monitoring.task_update", json.dumps(task_data).encode())
            
        await asyncio.sleep(random.uniform(3, 8))

async def main():
    try:
        nc = await nats.connect("localhost")
        print("[SIMULATOR] Connected to NATS")
        
        agents = [
            ("RECRUITER_01", "NODE_01", "RECRUITER"),
            ("COORDINATOR_A", "NODE_02", "OPS"),
            ("RESEARCHER_BOT", "NODE_01", "RESEARCH")
        ]
        
        tasks = [simulate_agent(nc, n, nd, r) for n, nd, r in agents]
        await asyncio.gather(*tasks)
        
    except Exception as e:
        print(f"[SIMULATOR] Error: {e}")

if __name__ == "__main__":
    asyncio.run(main())
