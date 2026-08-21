# Skills window

Sesefus marketplace item. One job: see agent skills, open their folders.

Not the store. Not the scanner. Own window on `:8788`.

## Open

```bat
Skills.bat
```

or

```bat
python host.py
```

Grok (`~/.grok/skills`) is wired. Bundled Grok skills show if that folder exists.

## Add Claude, Cursor, or any dir

1. Open the **providers.json** chip (app folder).
2. Copy a provider object from `providers.example.json`.
3. Save. Press **Reload**.

No code change. Same shape every time: `id`, `label`, `enabled`, `roots[]` with `id` / `label` / `path`.

Or POST:

```json
POST /api/providers
{
  "id": "claude",
  "label": "Claude",
  "enabled": true,
  "roots": [{ "id": "user", "label": "Claude skills", "path": "~/.claude/skills", "optional": true }]
}
```

## Tests

```bat
python -m unittest discover -s tests -v
```
