import json
import os
import numpy as np
from sklearn.decomposition import PCA
from collections import Counter

def analyze_noise():
    vector_path = '/mnt/c/Users/bardw/arcadium-circadia/ingest/vector_shards.jsonl'
    debris_path = '/mnt/c/Users/bardw/arcadium-circadia/ingest/debris_shards.jsonl'
    
    print("Loading vectors for noise analysis...")
    ids = []
    embeddings = []
    with open(vector_path, 'r', encoding='utf-8') as f:
        for line in f:
            data = json.loads(line)
            ids.append(data['chunk_id'])
            embeddings.append(data['embedding'])
    
    X = np.array(embeddings)
    pca = PCA(n_components=3)
    projected = pca.fit_transform(X)
    
    # Analyze the clusters
    # We'll look at the shards in the 'extreme' bins to see if they are noise
    noise_patterns = Counter()
    
    # Load debris to correlate content
    id_to_metadata = {}
    with open(debris_path, 'r', encoding='utf-8') as f:
        for line in f:
            shard = json.loads(line)
            id_to_metadata[shard['id']] = {
                'path': shard['source_path'],
                'preview': shard['content'][:100]
            }

    print("\n--- SEMANTIC NOISE ANALYSIS ---")
    for factor in range(3):
        # Find 5th and 95th percentiles
        low_thresh = np.percentile(projected[:, factor], 10)
        high_thresh = np.percentile(projected[:, factor], 90)
        
        for side in ['Low', 'High']:
            thresh = low_thresh if side == 'Low' else high_thresh
            indices = np.where(projected[:, factor] <= thresh)[0] if side == 'Low' else np.where(projected[:, factor] >= thresh)[0]
            print(f"\nAnalyzing Factor {factor} {side} (Threshold: {thresh:.2f}, Sample Size: {len(indices)})")
            
            sample_paths = []
            for idx in indices[:50]:
                cid = ids[idx]
                if cid in id_to_metadata:
                    path = id_to_metadata[cid]['path']
                    sample_paths.append(path)
            
            # Common file extensions or keywords in this cluster
            for path in sample_paths:
                ext = os.path.splitext(path)[1]
                if ext: noise_patterns[ext] += 1
                if 'Windows' in path: noise_patterns['[PATH:Windows]'] += 1
                if 'Program Files' in path: noise_patterns['[PATH:ProgFiles]'] += 1
                if 'AppData' in path: noise_patterns['[PATH:AppData]'] += 1

    print("\nRecommended Pruning Candidates (Top Patterns in Extreme Clusters):")
    for pattern, count in noise_patterns.most_common(10):
        print(f"- {pattern}: {count} occurrences")

if __name__ == '__main__':
    analyze_noise()
