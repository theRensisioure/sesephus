import os
import uuid
import hashlib
import json
from datetime import datetime

# Simple representation of the DebrisChunk proto
class DebrisChunk:
    def __init__(self, content, source_node, source_path, file_type, metadata=None):
        self.id = hashlib.sha256(content.encode()).hexdigest()
        self.content = content
        self.source_node = source_node
        self.source_path = source_path
        self.file_type = file_type
        self.timestamp = datetime.utcnow().isoformat()
        self.metadata = metadata or {}

    def to_dict(self):
        return {
            "id": self.id,
            "content": self.content,
            "source_node": self.source_node,
            "source_path": self.source_path,
            "file_type": self.file_type,
            "timestamp": self.timestamp,
            "metadata": self.metadata
        }

class Sieve:
    def __init__(self, root_dir, source_node="VisionOxide"):
        self.root_dir = root_dir
        self.source_node = source_node
        self.chunks = []

    def shred_text(self, content, file_path, file_type):
        # Shred by paragraphs (double newlines)
        paragraphs = content.split('\n\n')
        for i, para in enumerate(paragraphs):
            para = para.strip()
            if para:
                chunk = DebrisChunk(
                    content=para,
                    source_node=self.source_node,
                    source_path=file_path,
                    file_type=file_type,
                    metadata={"index": i, "shred_method": "paragraph"}
                )
                self.chunks.append(chunk)

    def shred_code(self, content, file_path, file_type):
        # Simple shredding by lines/blocks for now
        # Future improvement: Use AST for function/class level shredding
        lines = content.split('\n')
        buffer = []
        block_idx = 0
        for line in lines:
            buffer.append(line)
            if line.strip() == "" and len(buffer) > 5:
                content_block = "\n".join(buffer).strip()
                if content_block:
                    chunk = DebrisChunk(
                        content=content_block,
                        source_node=self.source_node,
                        source_path=file_path,
                        file_type=file_type,
                        metadata={"block_index": block_idx, "shred_method": "line_block"}
                    )
                    self.chunks.append(chunk)
                    block_idx += 1
                buffer = []
        
        # Final block
        if buffer:
            content_block = "\n".join(buffer).strip()
            if content_block:
                chunk = DebrisChunk(
                    content=content_block,
                    source_node=self.source_node,
                    source_path=file_path,
                    file_type=file_type,
                    metadata={"block_index": block_idx, "shred_method": "final_block"}
                )
                self.chunks.append(chunk)

    def scan(self):
        for root, dirs, files in os.walk(self.root_dir):
            if 'venv' in dirs:
                dirs.remove('venv') # Skip venv
            
            for file in files:
                file_path = os.path.join(root, file)
                file_type = os.path.splitext(file)[1]
                
                try:
                    with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
                        content = f.read()
                        
                    if file_type in ['.py', '.js', '.rs', '.go']:
                        self.shred_code(content, file_path, file_type)
                    elif file_type in ['.txt', '.md', '']: # No ext often log/debris
                        self.shred_text(content, file_path, file_type)
                    else:
                        # General shredding for unknown types
                        self.shred_text(content, file_path, file_type)
                        
                except Exception as e:
                    print(f"Failed to shred {file_path}: {e}")

    def ship(self, output_path):
        with open(output_path, 'w', encoding='utf-8') as f:
            for chunk in self.chunks:
                f.write(json.dumps(chunk.to_dict()) + '\n')
        print(f"Shipped {len(self.chunks)} chunks to {output_path}")

if __name__ == "__main__":
    sieve = Sieve("/mnt/c/Users/bardw/arcadium-circadia")
    sieve.scan()
    sieve.ship("/mnt/c/Users/bardw/arcadium-circadia/ingest/debris_shards.jsonl")
