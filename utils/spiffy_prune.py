import json
import os
import numpy as np
from sklearn.decomposition import PCA
from collections import Counter

def spiffy_pruner():
    current_dir = os.path.dirname(os.path.abspath(__file__))
    project_root = os.path.dirname(current_dir)
    vector_path = os.path.join(project_root, 'ingest', 'vector_shards.jsonl')
    debris_path = os.path.join(project_root, 'ingest', 'debris_shards.jsonl')
    
    print("Initiating Spiffy Noise Analysis...")
    
    # Load a substantial sample for analysis (10k shards)
    ids = []
    embeddings = []
    limit = 10000
    with open(vector_path, 'r', encoding='utf-8') as f:
        for i, line in enumerate(f):
            if i >= limit: break
            data = json.loads(line)
            ids.append(data['chunk_id'])
            embeddings.append(data['embedding'])
    
    X = np.array(embeddings)
    pca = PCA(n_components=3)
    projected = pca.fit_transform(X)
    
    # Identify the outliers (top/bottom 15%)
    noise_patterns = Counter()
    
    # Load debris metadata
    id_to_metadata = {}
    with open(debris_path, 'r', encoding='utf-8') as f:
        for line in f:
            shard = json.loads(line)
            if shard['id'] in ids:
                id_to_metadata[shard['id']] = shard['source_path']

    # We define 'Noise' as the extreme clusters that are dominated by specific paths
    for factor in range(3):
        low_thresh = np.percentile(projected[:, factor], 15)
        high_thresh = np.percentile(projected[:, factor], 85)
        
        for side, thresh in [('Low', low_thresh), ('High', high_thresh)]:
            indices = np.where(projected[:, factor] <= thresh)[0] if side == 'Low' else np.where(projected[:, factor] >= thresh)[0]
            
            for idx in indices:
                cid = ids[idx]
                if cid in id_to_metadata:
                    path = id_to_metadata[cid]
                    # Extract the directory or file extension as a potential noise pattern
                    parts = path.split(os.sep)
                    if len(parts) > 2:
                        noise_patterns[parts[1]] += 1 # Catch top-level dirs like 'Windows' or 'AppData'
                    ext = os.path.splitext(path)[1]
                    if ext: noise_patterns[f"EXT:{ext}"] += 1

    # Get the top noise patterns
    spiffy_filters = [p for p, c in noise_patterns.most_common(15) if c > (limit * 0.05)]
    
    print("\n--- SPIFFY PRUNING REPORT ---")
    print(f"Identified {len(spiffy_filters)} primary noise patterns in the latent space:")
    for f in spiffy_filters:
        print(f" - {f}")

    # Update the Forge to include these filters
    return spiffy_filters

if __name__ == '__main__':
    filters = spiffy_pruner()
    # Path to forge.py to update it with the new filters
    current_dir = os.path.dirname(os.path.abspath(__file__))
    project_root = os.path.dirname(current_dir)
    forge_path = os.path.join(project_root, 'utils', 'forge.py')
    
    if os.path.exists(forge_path):
        with open(forge_path, 'r', encoding='utf-8') as f:
            content = f.read()
        
        filter_str = json.dumps(filters)
        # Surgical injection of the filter list
        updated_content = content.replace("processed_ids = set()", f"noise_filters = {filter_str}\n    processed_ids = set()")
        
        # Add the filter check logic
        filter_check = """
            # Spiffy Pruning: Skip known noise patterns
            if any(nf in shard['source_path'] for nf in noise_filters):
                continue
        """
            
        # Insert before the content processing
        final_content = updated_content.replace("content = shard['content'].strip()", f"{filter_check}\n            content = shard['content'].strip()")
        
        with open(forge_path, 'w', encoding='utf-8') as f:
            f.write(final_content)
        
        print("\nForge.py has been SPIFFED. The system will now auto-prune noise in the second pass.")
