import json
import urllib.request
import urllib.parse
import os
import time
import sys

def forge_trinity(instance_index=0, total_instances=1):
    """
    Parallel 'Embrace Friction' Forge. 
    Part of a 3-node swarm processing the same queue.
    """
    input_path = '/mnt/c/Users/bardw/arcadium-circadia/ingest/debris_shards.jsonl'
    output_path = '/mnt/c/Users/bardw/arcadium-circadia/ingest/vector_shards.jsonl'
    model = 'nomic-embed-text'
    url = 'http://127.0.0.1:11434/api/embed'
    
    # DOCTRINAL FRICTION SETTINGS
    batch_size = 10         
    friction_delay = 1.0    
    
    # SPIFFY NOISE FILTERS (REMOVED 'mnt' because it killed the whole drive)
    noise_filters = [".pyc", "Windows", "AppData", "Program Files"]
    
    processed_count = 0
    error_count = 0
    
    if not os.path.exists(input_path):
        print(f'Input file {input_path} not found')
        return

    # Checkpoint Resume
    processed_ids = set()
    if os.path.exists(output_path):
        with open(output_path, 'r', encoding='utf-8') as f:
            for line in f:
                try:
                    data = json.loads(line)
                    processed_ids.add(data['chunk_id'])
                except:
                    continue
    
    print(f"FORGE NODE {instance_index}/{total_instances} ACTIVE")
    print(f"Resuming with {len(processed_ids)} established vectors.")

    with open(input_path, 'r', encoding='utf-8') as infile, open(output_path, 'a', encoding='utf-8') as outfile:
        current_batch = []
        for line in infile:
            try:
                shard = json.loads(line)
            except json.JSONDecodeError:
                continue
            
            if shard['id'] in processed_ids:
                continue

            if int(shard['id'][:8], 16) % total_instances != instance_index:
                continue

            # Spiffy Pruning
            source_path = shard['source_path']
            is_noise = False
            for nf in noise_filters:
                if nf in source_path:
                    is_noise = True
                    break
            
            if is_noise:
                continue

            content = shard['content'].strip()
            if not content: continue
            if len(content) > 30000: content = content[:30000]

            current_batch.append(shard)

            if len(current_batch) >= batch_size:
                input_texts = [s['content'] for s in current_batch]
                data = json.dumps({'model': model, 'input': input_texts}).encode('utf-8')
                req = urllib.request.Request(url, data=data, headers={'Content-Type': 'application/json'})
                
                try:
                    with urllib.request.urlopen(req) as response:
                        res_data = json.loads(response.read().decode('utf-8'))
                        embeddings = res_data.get('embeddings', [])
                        for i, emb in enumerate(embeddings):
                            vector_shard = {
                                'chunk_id': current_batch[i]['id'],
                                'embedding': emb,
                                'model_name': model,
                                'dimensions': len(emb)
                            }
                            outfile.write(json.dumps(vector_shard) + '\n')
                        
                        processed_count += len(current_batch)
                        if processed_count % 100 == 0:
                            print(f'Node {instance_index}: {processed_count} shards vectorized...')
                except Exception as e:
                    error_count += 1
                
                time.sleep(friction_delay)
                current_batch = []
    
    print(f'Node {instance_index} Task Complete.')

if __name__ == '__main__':
    idx = int(sys.argv[1]) if len(sys.argv) > 1 else 0
    total = int(sys.argv[2]) if len(sys.argv) > 2 else 1
    forge_trinity(idx, total)
