import time
import json
import os
import psutil
import subprocess

class SubstrateMonitor:
    """
    Monitors the local hardware substrate (CPU, GPU, RAM) 
    during Jigsaw Synthesis operations.
    """
    def __init__(self, log_path=None):
        if log_path is None:
            current_dir = os.path.dirname(os.path.abspath(__file__))
            project_root = os.path.dirname(current_dir)
            log_path = os.path.join(project_root, 'ingest', 'telemetry.jsonl')
        self.log_path = log_path
        self.has_gpu = self._check_gpu()

    def _check_gpu(self):
        try:
            subprocess.check_output(['nvidia-smi'])
            return True
        except:
            return False

    def get_gpu_stats(self):
        if not self.has_gpu:
            return None
        try:
            # Query nvidia-smi for load and memory
            res = subprocess.check_output([
                'nvidia-smi', 
                '--query-gpu=utilization.gpu,memory.used,memory.total,temperature.gpu', 
                '--format=csv,noheader,nounits'
            ]).decode('utf-8').strip().split(', ')
            return {
                "gpu_load_pct": float(res[0]),
                "vram_used_mb": int(res[1]),
                "vram_total_mb": int(res[2]),
                "gpu_temp_c": int(res[3])
            }
        except:
            return {"error": "GPU query failed"}

    def get_stats(self):
        stats = {
            "timestamp": time.time(),
            "cpu_load_pct": psutil.cpu_percent(interval=None),
            "ram_used_gb": round(psutil.virtual_memory().used / (1024**3), 2),
            "ram_total_gb": round(psutil.virtual_memory().total / (1024**3), 2),
        }
        gpu = self.get_gpu_stats()
        if gpu:
            stats.update(gpu)
        return stats

    def run(self, interval=5):
        print(f"Substrate Monitor ACTIVE. Logging to {self.log_path}")
        print("Press Ctrl+C to stop (if running in foreground).")
        
        # Ensure directory exists
        os.makedirs(os.path.dirname(self.log_path), exist_ok=True)

        with open(self.log_path, 'a', encoding='utf-8') as f:
            while True:
                stats = self.get_stats()
                f.write(json.dumps(stats) + '\n')
                f.flush()
                
                # Console output for immediate feedback
                gpu_info = f" | GPU: {stats.get('gpu_load_pct')}% @ {stats.get('gpu_temp_c')}C" if self.has_gpu else ""
                print(f"[{time.strftime('%H:%M:%S')}] CPU: {stats['cpu_load_pct']}% | RAM: {stats['ram_used_gb']}GB{gpu_info}")
                
                time.sleep(interval)

if __name__ == "__main__":
    monitor = SubstrateMonitor()
    monitor.run()
