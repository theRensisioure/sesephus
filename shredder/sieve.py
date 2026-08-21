import os
import hashlib
import json
import argparse
from datetime import datetime, timezone

# Binary file extensions to skip (never attempt text read)
SKIP_BINARY_EXTS = {
    '.exe', '.dll', '.jar', '.zip', '.rar', '.7z', '.tar', '.gz', '.bz2',
    '.png', '.jpg', '.jpeg', '.gif', '.bmp', '.ico', '.webp', '.svgz',
    '.lnk', '.dat', '.mca', '.nbt', '.ttf', '.otf', '.eot', '.woff', '.woff2',
    '.pdb', '.class', '.pyc', '.pyo', '.so', '.dylib', '.wasm', '.bin',
    '.mp3', '.wav', '.flac', '.ogg', '.mp4', '.mov', '.avi', '.mkv', '.webm',
    '.pdf', '.doc', '.docx', '.xls', '.xlsx', '.ppt', '.pptx',
    '.db', '.sqlite', '.bak', '.tmp',
    '.url',  # desktop internet shortcuts are not primary content
}

# Simple representation of the DebrisChunk proto
class DebrisChunk:
    def __init__(self, content, source_node, source_path, file_type, metadata=None):
        self.id = hashlib.sha256(content.encode()).hexdigest()
        self.content = content
        self.source_node = source_node
        self.source_path = source_path
        self.file_type = file_type
        self.timestamp = datetime.now(timezone.utc).isoformat()
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
            # Skip noisy / bulk dirs (venv, extracted programs, large game installs)
            dirs[:] = [d for d in dirs if not (
                d.lower() in ('venv', 'program files', 'node_modules', '__pycache__', 'libraries', 'versions', 'mods')
                or 'bmc2' in d.lower() or 'server_pack' in d.lower()
            )]
            
            for file in files:
                file_path = os.path.join(root, file)
                file_type = os.path.splitext(file)[1].lower()
                
                if file_type in SKIP_BINARY_EXTS:
                    continue
                
                # Binary content probe (null byte => binary)
                try:
                    with open(file_path, 'rb') as fb:
                        head = fb.read(4096)
                    if b'\0' in head:
                        continue
                except Exception:
                    continue
                
                try:
                    with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
                        content = f.read()
                        
                    if file_type in ['.py', '.js', '.rs', '.go']:
                        self.shred_code(content, file_path, file_type)
                    elif file_type in ['.txt', '.md', '']: # No ext often log/debris
                        self.shred_text(content, file_path, file_type)
                    else:
                        # General shredding for unknown types (incl .json .toml .snbt .html etc)
                        self.shred_text(content, file_path, file_type)
                        
                except Exception as e:
                    print(f"Failed to shred {file_path}: {e}")

    def ship(self, output_path):
        with open(output_path, 'w', encoding='utf-8') as f:
            for chunk in self.chunks:
                f.write(json.dumps(chunk.to_dict()) + '\n')
        print(f"Shipped {len(self.chunks)} chunks to {output_path}")

if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="Sieve: shred text files under a root into DebrisChunks (jsonl) for sesefus ingest."
    )
    parser.add_argument(
        "--root", default=None,
        help="Directory tree to scan (default: the sesefus project itself)"
    )
    parser.add_argument(
        "--output", default=None,
        help="Path to write debris_shards.jsonl (default: <sesefus>/ingest/debris_shards.jsonl)"
    )
    parser.add_argument(
        "--source-node", default="Desktop",
        help="Label for source_node in chunks (default: Desktop when using --root)"
    )
    args = parser.parse_args()

    script_dir = os.path.dirname(os.path.abspath(__file__))
    sesefus_root = os.path.dirname(script_dir)

    root_dir = args.root or sesefus_root
    if args.output:
        output_path = args.output
    else:
        ingest_dir = os.path.join(sesefus_root, "ingest")
        os.makedirs(ingest_dir, exist_ok=True)
        output_path = os.path.join(ingest_dir, "debris_shards.jsonl")

    # If user gave explicit root and no explicit source, use a descriptive node
    source_node = args.source_node
    if args.root and args.source_node == "Desktop":
        # keep "Desktop" as sensible default for desktop ingest
        pass

    print(f"Sieve starting: root={root_dir}")
    sieve = Sieve(root_dir, source_node=source_node)
    sieve.scan()
    sieve.ship(output_path)
