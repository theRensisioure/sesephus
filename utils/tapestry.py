import json
import os
import numpy as np
from sklearn.decomposition import PCA
def tapestry():
    current_dir = os.path.dirname(os.path.abspath(__file__))
    project_root = os.path.dirname(current_dir)
    vector_path = os.path.join(project_root, 'ingest', 'vector_shards.jsonl')
    debris_path = os.path.join(project_root, 'ingest', 'debris_shards.jsonl')
    output_root = os.path.join(project_root, 'SYNTHESIS')
    
    if not os.path.exists(vector_path):
        print(f"Vector shards not found at {vector_path}. Is the Forge finished?")
        return

    print("Loading vectors for dimensional reduction...")
    ids = []
    embeddings = []
    with open(vector_path, 'r', encoding='utf-8') as f:
        for line in f:
            data = json.loads(line)
            ids.append(data['chunk_id'])
            embeddings.append(data['embedding'])
    
    X = np.array(embeddings)
    
    # We use PCA to find the 'smallest common factors' (Principal Components)
    # Factor 1: The most dominant theme variance
    # Factor 2: The second most dominant, etc.
    n_factors = 3 
    print(f"Extracting {n_factors} primary semantic factors from {len(X)} shards...")
    pca = PCA(n_components=n_factors)
    projected = pca.fit_transform(X)
    
    # Create a mapping of ID to its projected coordinates
    # We will 'bin' these coordinates to create a directory tree
    # e.g., High/Medium/Low for each factor
    bins = 3 # High, Mid, Low
    
    def get_bin_name(val, factor_idx):
        if val > 0.5: return f"F{factor_idx}_High"
        if val < -0.5: return f"F{factor_idx}_Low"
        return f"F{factor_idx}_Mid"

    id_to_path = {}
    for i, id in enumerate(ids):
        path_parts = [get_bin_name(projected[i, j], j) for j in range(n_factors)]
        id_to_path[id] = os.path.join(*path_parts)

    print("Projecting shards into factor-based directory tree...")
    if not os.path.exists(output_root):
        os.makedirs(output_root)

    # Process debris shards and project them
    with open(debris_path, 'r', encoding='utf-8') as f:
        for line in f:
            shard = json.loads(line)
            chunk_id = shard['id']
            if chunk_id in id_to_path:
                rel_path = id_to_path[chunk_id]
                node_dir = os.path.join(output_root, rel_path)
                
                if not os.path.exists(node_dir):
                    os.makedirs(node_dir)
                
                preview = "".join(x for x in shard['content'][:30] if x.isalnum() or x in " -_").strip()
                filename = f"{chunk_id[:8]}_{preview}.txt"
                
                shard_file = os.path.join(node_dir, filename)
                with open(shard_file, 'w', encoding='utf-8') as sf:
                    sf.write(f"SOURCE: {shard['source_path']}\n")
                    sf.write("-" * 40 + "\n\n")
                    sf.write(shard['content'])
    
    print(f"Tapestry Complete: Life's work projected into {output_root}")

if __name__ == '__main__':
    tapestry()
