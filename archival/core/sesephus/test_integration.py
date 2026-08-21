import subprocess
import time
import os
import sys
import urllib.request
import json
import shutil

def main():
    print("=== SESEPHUS AUTOMATED INTEGRATION TEST ===")
    
    # 1. Clean up old files
    vault_path = "V:\\sesephus_vault.db"
    if os.path.exists(vault_path):
        os.remove(vault_path)
        print(f"Cleaned up old vault: {vault_path}")
        
    recordings_dir = "recordings"
    if os.path.exists(recordings_dir):
        shutil.rmtree(recordings_dir)
        print(f"Cleaned up local recordings folder: {recordings_dir}")

    # Paths to binaries
    host_bin = os.path.join("zig-out", "bin", "host.exe")
    client_bin = os.path.join("zig-out", "bin", "client.exe")

    if not os.path.exists(host_bin) or not os.path.exists(client_bin):
        print("Error: Binaries not found. Run 'zig build' first.")
        sys.exit(1)

    # 1.5 Spawn Dashboard Server (on port 3001)
    print("Launching Dashboard/Transcription Sidecar...")
    python_bin = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "venv", "Scripts", "python.exe"))
    if not os.path.exists(python_bin):
        python_bin = sys.executable
    dashboard_script = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "dashboard", "dashboard_server.py"))
    dashboard_log = open("dashboard.log", "w", encoding="utf-8")
    dashboard_proc = subprocess.Popen(
        [python_bin, "-u", dashboard_script],
        stdout=dashboard_log,
        stderr=subprocess.STDOUT,
        text=True
    )

    # 2. Spawn Host Process (No password needed)
    print("Launching Host Daemon...")
    host_log = open("host.log", "w", encoding="utf-8")
    host_proc = subprocess.Popen(
        [host_bin],
        stdin=subprocess.PIPE,
        stdout=host_log,
        stderr=subprocess.STDOUT,
        text=True,
        bufsize=1
    )

    # Sleep briefly to let host initialize the database
    time.sleep(2)

    # 3. Spawn Client Process
    print("Launching Client Daemon...")
    client_log = open("client.log", "w", encoding="utf-8")
    client_proc = subprocess.Popen(
        [client_bin, "--name", "test-client", "--non-interactive"],
        stdin=subprocess.PIPE,
        stdout=client_log,
        stderr=subprocess.STDOUT,
        text=True,
        bufsize=1
    )

    # Wait for client to connect
    time.sleep(2)

    # 4. Verify HTTP Status API is running and shows the client
    print("Querying HTTP Status API...")
    try:
        response = urllib.request.urlopen("http://localhost:3000/api/status")
        status_data = json.loads(response.read().decode())
        print("HTTP Status API Response:", status_data)
        
        clients = status_data.get("clients", [])
        active_clients = [c for c in clients if c.get("client_id") == "test-client" and c.get("active")]
        if active_clients:
            print("[OK] HTTP API successfully registered active client 'test-client'.")
        else:
            print("[ERROR] 'test-client' not active in HTTP status.")
            sys.exit(1)
    except Exception as e:
        print(f"[ERROR] Failed to query HTTP status API: {e}")
        sys.exit(1)

    # 5. Schedule an alarm on the Host
    alarm_cmd = "alarm test-client 2 record_audio 3.0\n"
    print(f"Sending alarm command to Host: {alarm_cmd.strip()}")
    host_proc.stdin.write(alarm_cmd)
    host_proc.stdin.flush()

    # Wait 8 seconds for:
    # - 2s: alarm trigger delay
    # - 3s: audio recording duration
    # - 3s: network sync and database logging
    print("Waiting 8 seconds for alarm trigger, local recording, and database logging...")
    time.sleep(8)

    # 6. Shutdown the Host
    print("Sending exit command to Host...")
    host_proc.stdin.write("exit\n")
    host_proc.stdin.flush()

    # Wait for processes to exit
    try:
        host_proc.wait(timeout=5)
        print("Host exited.")
    except subprocess.TimeoutExpired:
        print("Force terminating Host...")
        host_proc.terminate()

    try:
        client_proc.wait(timeout=5)
        print("Client exited.")
    except subprocess.TimeoutExpired:
        print("Force terminating Client...")
        client_proc.terminate()

    try:
        dashboard_proc.wait(timeout=5)
        print("Dashboard exited.")
    except subprocess.TimeoutExpired:
        print("Force terminating Dashboard...")
        dashboard_proc.terminate()

    # Close log files
    host_log.close()
    client_log.close()
    dashboard_log.close()

    # Read output
    with open("host.log", "r", encoding="utf-8", errors="ignore") as f:
        host_stdout = f.read()
    with open("client.log", "r", encoding="utf-8", errors="ignore") as f:
        client_stdout = f.read()
    with open("dashboard.log", "r", encoding="utf-8", errors="ignore") as f:
        dashboard_stdout = f.read()

    print("\n--- HOST OUTPUT ---")
    print(host_stdout)
    print("-------------------")

    print("\n--- CLIENT OUTPUT ---")
    print(client_stdout)
    print("---------------------")

    print("\n--- DASHBOARD/TRANSCRIPTION OUTPUT ---")
    print(dashboard_stdout)
    print("--------------------------------------")

    # 7. Check if local recording exists on client side
    print("Checking local recordings directory...")
    if os.path.exists(recordings_dir):
        files = os.listdir(recordings_dir)
        print(f"Recordings found: {files}")
        if len(files) > 0 and files[0].endswith(".wav"):
            print(f"[OK] Client successfully saved local WAV file: {files[0]}")
        else:
            print("[ERROR] Local recordings folder empty or no WAV files found.")
            sys.exit(1)
    else:
        print("[ERROR] Local recordings folder does not exist.")
        sys.exit(1)

    # 8. Read and Verify the Vault Database (No password needed)
    print("\nVerifying vault database contents using Host --read-vault...")
    verify_proc = subprocess.Popen(
        [host_bin, "--read-vault"],
        stdin=subprocess.PIPE,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
        bufsize=1
    )
    
    verify_stdout, _ = verify_proc.communicate()
    print("\n--- VAULT VERIFICATION OUTPUT ---")
    print(verify_stdout)
    print("---------------------------------")

    # Perform assertions on output to confirm success
    if "Found 1 journal entries." in verify_stdout and "Local Path: recordings/journal_" in verify_stdout:
        print("\n[SUCCESS] Integration test passed! The alarm triggered, recorded locally, synced status metadata, and logged the local path securely.")
        sys.exit(0)
    else:
        print("\n[FAILURE] Integration test failed. The expected database entries or local path metadata were not found.")
        sys.exit(1)

if __name__ == "__main__":
    main()
