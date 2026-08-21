import subprocess
import time
import os
import sys
import urllib.request
import json

def make_post(url, data):
    req = urllib.request.Request(
        url,
        data=json.dumps(data).encode('utf-8'),
        headers={'Content-Type': 'application/json'}
    )
    with urllib.request.urlopen(req) as response:
        return json.loads(response.read().decode())

def make_get(url):
    with urllib.request.urlopen(url) as response:
        return json.loads(response.read().decode())

def main():
    print("=== SESEPHUS CIRCADIA ADVANCED INTEGRATION TEST ===")

    host_bin = os.path.join("zig-out", "bin", "host.exe")
    client_bin = os.path.join("zig-out", "bin", "client.exe")

    if not os.path.exists(host_bin) or not os.path.exists(client_bin):
        print("Error: Binaries not found. Run 'zig build' first.")
        sys.exit(1)

    # 1. Spawn Host Daemon
    print("Launching Host Daemon...")
    host_log = open("host_adv.log", "w", encoding="utf-8")
    host_proc = subprocess.Popen(
        [host_bin],
        stdin=subprocess.PIPE,
        stdout=host_log,
        stderr=subprocess.STDOUT,
        text=True,
        bufsize=1
    )

    time.sleep(2)

    # 2. Spawn two Client Daemons
    print("Launching Client Daemon 1...")
    client1_log = open("client1_adv.log", "w", encoding="utf-8")
    client1_proc = subprocess.Popen(
        [client_bin, "--name", "test-client-1", "--non-interactive", "--no-record"],
        stdin=subprocess.PIPE,
        stdout=client1_log,
        stderr=subprocess.STDOUT,
        text=True,
        bufsize=1
    )

    print("Launching Client Daemon 2...")
    client2_log = open("client2_adv.log", "w", encoding="utf-8")
    client2_proc = subprocess.Popen(
        [client_bin, "--name", "test-client-2", "--non-interactive", "--no-record"],
        stdin=subprocess.PIPE,
        stdout=client2_log,
        stderr=subprocess.STDOUT,
        text=True,
        bufsize=1
    )

    # Wait for registration
    time.sleep(2)

    # 3. Query Status and verify clients are online
    status_url = "http://127.0.0.1:3000/api/status"
    print(f"Querying status from {status_url}...")
    status = make_get(status_url)
    print("Clients registered:", [c["client_id"] for c in status["clients"]])
    
    cids = [c["client_id"] for c in status["clients"] if c["active"]]
    assert "test-client-1" in cids, "test-client-1 failed to register"
    assert "test-client-2" in cids, "test-client-2 failed to register"
    print("[OK] Both clients successfully registered.")

    # 4. Create a subgroup
    group_url = "http://127.0.0.1:3000/api/group"
    print("Creating subgroup 'Subgroup-A'...")
    group_payload = {
        "name": "Subgroup-A",
        "client_ids": ["test-client-1", "test-client-2"]
    }
    grp_res = make_post(group_url, group_payload)
    print("Create group response:", grp_res)
    assert grp_res["success"], "Failed to create group"
    group_id = grp_res["group_id"]
    print(f"[OK] Subgroup created with ID {group_id}.")

    # 5. Schedule an alarm targeted at the subgroup
    alarm_url = "http://127.0.0.1:3000/api/alarm"
    print("Scheduling alarm for Subgroup-A to fire in 2 seconds...")
    alarm_payload = {
        "seconds": 2,
        "action": "play_sound",
        "duration": 1.0,
        "group_id": group_id
    }
    alarm_res = make_post(alarm_url, alarm_payload)
    print("Schedule alarm response:", alarm_res)
    assert alarm_res["success"], "Failed to schedule group alarm"

    # Wait 3 seconds for alarm to fire
    print("Waiting 3 seconds for alarm to dispatch to subgroup...")
    time.sleep(3)

    # 6. Verify alarm fired and client logs contain beep trigger
    client1_log.close()
    client2_log.close()

    with open("client1_adv.log", "r", encoding="utf-8") as f:
        c1_out = f.read()
    with open("client2_adv.log", "r", encoding="utf-8") as f:
        c2_out = f.read()

    assert "ALARM TRIGGERED!" in c1_out, "test-client-1 did not trigger alarm"
    assert "ALARM TRIGGERED!" in c2_out, "test-client-2 did not trigger alarm"
    print("[OK] Alarm successfully dispatched and triggered concurrently on all subgroup clients.")

    # Reopen log files for tailing
    client1_log = open("client1_adv.log", "a", encoding="utf-8")
    client2_log = open("client2_adv.log", "a", encoding="utf-8")

    # 7. Create an Interval Alarm Sequence
    interval_url = "http://127.0.0.1:3000/api/alarm/create_interval"
    print("Creating interval sequence of 4 alarms over 10 seconds...")
    interval_payload = {
        "client_ids": ["test-client-1"],
        "duration_sec": 10,
        "count": 4,
        "action": "play_sound",
        "action_duration": 1.0
    }
    t0 = time.time()
    int_res = make_post(interval_url, interval_payload)
    t1 = time.time()
    print("Interval sequence creation response:", int_res, "took:", t1 - t0)
    assert int_res["success"], "Failed to create interval alarms"
    parent_id = int_res["parent_id"]

    # Verify alarms are created and share parent_id
    t2 = time.time()
    status = make_get(status_url)
    t3 = time.time()
    print("Get status took:", t3 - t2)
    seq_alarms = [a for a in status["alarms"] if a["parent_id"] == parent_id]
    print(f"Found {len(seq_alarms)} alarms with parent ID {parent_id}:")
    for a in seq_alarms:
        print(f"  Alarm ID: {a['alarm_id']}, trigger_time: {a['trigger_time']}, fired: {a['fired']}")
    assert len(seq_alarms) == 4, f"Expected 4 interval alarms, found {len(seq_alarms)}"

    # 8. Adjust spacing of interval alarms post-creation
    adjust_url = "http://127.0.0.1:3000/api/alarm/adjust_interval"
    print(f"Respacing pending alarms of parent ID {parent_id} to 20 seconds intervals...")
    adjust_payload = {
        "parent_id": parent_id,
        "spacing_sec": 20.0
    }
    t4 = time.time()
    adj_res = make_post(adjust_url, adjust_payload)
    t5 = time.time()
    print("Respace response:", adj_res, "took:", t5 - t4, "Total elapsed since create:", t5 - t0)

    # Verify trigger times were respaced
    status = make_get(status_url)
    seq_alarms_after = sorted([a for a in status["alarms"] if a["parent_id"] == parent_id], key=lambda x: x["trigger_time"])
    diffs = [seq_alarms_after[i+1]["trigger_time"] - seq_alarms_after[i]["trigger_time"] for i in range(len(seq_alarms_after)-1)]
    print("Interval spacing diffs (ms):", diffs)
    for d in diffs:
        assert abs(d - 20000) < 500, f"Expected ~20000ms spacing, got {d}ms"
    print("[OK] Interval sequence successfully respaced post-creation.")

    # 9. Test Bulk Disable
    bulk_url = "http://127.0.0.1:3000/api/alarm/edit"
    alarm_ids = [a["alarm_id"] for a in seq_alarms_after]
    print(f"Bulk disabling interval alarms {alarm_ids}...")
    bulk_payload = {
        "alarm_ids": alarm_ids,
        "enabled": False
    }
    bulk_res = make_post(bulk_url, bulk_payload)
    assert bulk_res["success"], "Failed to bulk edit alarms"
    
    # Verify disabled status
    status = make_get(status_url)
    for a in status["alarms"]:
        if a["alarm_id"] in alarm_ids:
            assert not a["enabled"], f"Alarm {a['alarm_id']} was not disabled"
    print("[OK] Alarms bulk disabled successfully.")

    # 10. Test Toggle All
    toggle_url = "http://127.0.0.1:3000/api/alarm/toggle_all"
    print("Toggle all alarms to enabled...")
    toggle_res = make_post(toggle_url, {"enabled": True})
    assert toggle_res["success"], "Failed to toggle all alarms"

    status = make_get(status_url)
    for a in status["alarms"]:
        if not a["fired"]:
            assert a["enabled"], f"Alarm {a['alarm_id']} should be enabled"
    print("[OK] Toggle-all enabled successfully.")

    # Cleanup
    print("Shutting down processes...")
    host_proc.stdin.write("exit\n")
    host_proc.stdin.flush()
    try:
        host_proc.wait(timeout=3)
    except subprocess.TimeoutExpired:
        host_proc.terminate()

    client1_proc.terminate()
    client2_proc.terminate()
    client1_log.close()
    client2_log.close()
    host_log.close()

    print("\n[SUCCESS] Advanced integration tests passed!")
    sys.exit(0)

if __name__ == "__main__":
    main()
