# GUIDE: Programmatic Engagement with Vector Shards
## Subject: Semantic Interaction & Retrieval Logic

The `vector_shards.jsonl` file is the mathematical soul of the Jigsaw Engine. It contains the 768-dimensional coordinates of your life's work. This guide explains how to navigate this space using Python and NumPy.

---

### 1. Data Structure
The file is in **JSONL** (JSON Lines) format. Each line is an independent object:
```json
{
  "chunk_id": "sha256_hash",
  "embedding": [0.123, -0.456, ...],
  "model_name": "nomic-embed-text",
  "dimensions": 768
}
```

### 2. Loading the Latent Space
To perform operations (like clustering or search), you must load the vectors into a NumPy array.

```python
import json
import numpy as np

def load_vectors(path='ingest/vector_shards.jsonl'):
    ids = []
    embeddings = []
    with open(path, 'r', encoding='utf-8') as f:
        for line in f:
            data = json.loads(line)
            ids.append(data['chunk_id'])
            embeddings.append(data['embedding'])
    return ids, np.array(embeddings)
```

### 3. Semantic Search (Cosine Similarity)
To find shards that are semantically related to a new prompt or another shard:

```python
def find_nearest(target_vector, all_embeddings, top_k=5):
    # Calculate cosine similarity
    # (Dot product of normalized vectors)
    norm_target = target_vector / np.linalg.norm(target_vector)
    norm_all = all_embeddings / np.linalg.norm(all_embeddings, axis=1, keepdims=True)
    
    similarities = np.dot(norm_all, norm_target)
    nearest_indices = np.argsort(similarities)[::-1][:top_k]
    
    return nearest_indices, similarities[nearest_indices]
```

### 4. Retrieving the Content (The Bridge)
The `chunk_id` in the vector file is a direct pointer to the `id` in `debris_shards.jsonl`. To get the human-readable text back:

```python
def get_content(chunk_id, debris_path='ingest/debris_shards.jsonl'):
    with open(debris_path, 'r', encoding='utf-8') as f:
        for line in f:
            shard = json.loads(line)
            if shard['id'] == chunk_id:
                return shard['content'], shard['source_path']
    return None, None
```

### 5. Overdubbing the Result
By combining these steps, you can create a "Sovereign Search" tool:
1. **Vectorize** a user's question locally (via Ollama).
2. **Find** the nearest `chunk_id` in your local shards.
3. **Overdub** the context: Read the 3-5 nearest shards and present them to the LLM for a zero-trust, local-only response.

### 6. Substrate Considerations
- **Memory:** 100k vectors (768-dim) will take ~300MB of RAM.
- **Speed:** NumPy can calculate cosine similarity for 100k vectors in milliseconds.
- **Latency:** The bottleneck is usually the initial vectorization (The Forge). Retrieval is near-instant.

---
*End of Guide*
