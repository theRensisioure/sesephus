import subprocess
import time
import os
import sys
import json

def main():
    print("=== SESEPHUS STRUCTURED EXPORT TEST ===")
    
    # 1. Clean up old files (guarded: refuses to delete a real vault — see
    #    _vault_test_safety. Override path with SESEPHUS_TEST_VAULT for a sandbox.)
    from _vault_test_safety import resolve_test_vault, safe_reset_vault, safe_reset_dir
    vault_path = resolve_test_vault("sesephus_vault.db")
    safe_reset_vault(vault_path)

    recordings_dir = "recordings"
    safe_reset_dir(recordings_dir)

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
    
    dashboard_log = open("dashboard_export.log", "w", encoding="utf-8")
    dashboard_proc = subprocess.Popen(
        [python_bin, "-u", dashboard_script],
        stdout=dashboard_log,
        stderr=subprocess.STDOUT,
        text=True
    )

    # 2. Spawn Host Process
    print("Launching Host Daemon...")
    host_log = open("host_export.log", "w", encoding="utf-8")
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

    # 3. Spawn Client Process (non-interactive so it captures and uploads directly)
    print("Launching Client Daemon...")
    client_log = open("client_export.log", "w", encoding="utf-8")
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

    # 4. Schedule alarm to trigger recording
    alarm_cmd = "alarm test-client 1 record_audio 2.0\n"
    print(f"Sending alarm command to Host: {alarm_cmd.strip()}")
    host_proc.stdin.write(alarm_cmd)
    host_proc.stdin.flush()

    # Wait 6 seconds for recording to finish and base64 upload to succeed
    print("Waiting 6 seconds for recording, upload and db write...")
    time.sleep(6)

    # 5. Shutdown client and host first
    print("Shutting down processes...")
    host_proc.stdin.write("exit\n")
    host_proc.stdin.flush()

    try:
        host_proc.wait(timeout=5)
    except subprocess.TimeoutExpired:
        host_proc.terminate()

    try:
        client_proc.wait(timeout=5)
    except subprocess.TimeoutExpired:
        client_proc.terminate()

    host_log.close()
    client_log.close()

    # 6. Run host in --structured mode while sidecar is STILL running!
    print("Running host in structured export mode...")
    export_proc = subprocess.Popen(
        [host_bin, "--structured"],
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True
    )
    
    export_stdout, export_stderr = export_proc.communicate()
    
    print("\n--- STRUCTURED EXPORT STDOUT ---")
    print(export_stdout)
    print("--------------------------------")
    print("\n--- STRUCTURED EXPORT STDERR ---")
    print(export_stderr)
    print("--------------------------------")

    # Now we can safely shut down the sidecar dashboard server
    try:
        dashboard_proc.terminate()
        dashboard_proc.wait(timeout=5)
    except Exception:
        pass
    dashboard_log.close()

    # 7. Assert and verify JSON
    try:
        journals = json.loads(export_stdout.strip())
    except json.JSONDecodeError as e:
        print(f"[FAILURE] Output is not valid JSON: {e}")
        sys.exit(1)

    if not isinstance(journals, list):
        print("[FAILURE] Output JSON is not an array.")
        sys.exit(1)

    if len(journals) == 0:
        print("[FAILURE] Output array is empty, expected 1 journal entry.")
        sys.exit(1)

    entry = journals[0]
    required_keys = ["client_id", "filename", "timestamp", "transcript"]
    for key in required_keys:
        if key not in entry:
            print(f"[FAILURE] Missing key '{key}' in journal entry: {entry}")
            sys.exit(1)

    print(f"[OK] Parsed journal entry successfully: {entry}")

    if entry["client_id"] != "test-client":
        print(f"[FAILURE] Expected client_id to be 'test-client', got '{entry['client_id']}'")
        sys.exit(1)

    if not entry["transcript"]:
        print("[FAILURE] Expected transcript to be non-empty.")
        sys.exit(1)

    if entry["transcript"] == "[Transcription Error]":
        print("[FAILURE] Transcript is a [Transcription Error]. Sidecar communication failed.")
        sys.exit(1)

    print("\n[SUCCESS] Structured export verification test passed!")
    sys.exit(0)

if __name__ == "__main__":
    main()
