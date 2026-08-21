import json
import re
import os

def prune_chat():
    input_path = '/mnt/c/Users/bardw/Documents/full_chat_export.json'
    output_path = '/mnt/c/Users/bardw/Documents/pruned_chat_manifest.txt'
    
    if not os.path.exists(input_path):
        print("Export file not found.")
        return

    print("Initiating Semantic Pruning...")
    with open(input_path, 'r', encoding='utf-8') as f:
        data = json.load(f)

    pruned_content = []
    
    for entry in data:
        # We only care about entries that contain actual messages
        if 'messages' in entry.get('$set', {}):
            messages = entry['$set']['messages']
        elif 'type' in entry:
            messages = [entry]
        else:
            continue

        for msg in messages:
            role = msg.get('type', 'unknown').upper()
            content_list = msg.get('content', [])
            
            # Extract the raw text
            raw_text = ""
            if isinstance(content_list, list):
                for item in content_list:
                    if isinstance(item, dict) and 'text' in item:
                        raw_text += item['text']
            elif isinstance(content_list, str):
                raw_text = content_list

            if not raw_text:
                continue

            # DOCTRINAL PRUNING: Remove low-density session context (directory trees)
            # This is the 'Windows Junk' of the chat logs.
            clean_text = re.sub(r'<session_context>.*?</session_context>', '[SYSTEM CONTEXT OMITTED]', raw_text, flags=re.DOTALL)
            
            # Optional: Keep thoughts for 'The Crucible' analysis
            thoughts = ""
            if 'thoughts' in msg:
                thought_summaries = [t.get('description', '') for t in msg['thoughts']]
                thoughts = f"\n[AI THOUGHTS: {' | '.join(thought_summaries)}]"

            pruned_content.append(f"--- {role} ---\n{clean_text.strip()}{thoughts}\n")

    print(f"Pruning complete. Reduced {len(data)} entries to {len(pruned_content)} semantic blocks.")
    
    with open(output_path, 'w', encoding='utf-8') as f:
        f.write("\n".join(pruned_content))
    
    print(f"Pruned manifest saved to {output_path}")

if __name__ == "__main__":
    prune_chat()
