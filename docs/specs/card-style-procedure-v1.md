# Card style procedure v1

Status: finalized for the prerelease card surface. Docs only. It adds no runtime.

This is how any card in the Zig card surface is styled. It sits beside
`card-surface-prerelease-v0.md` (what the surface is) and the deck rules there
(how a card behaves). It covers look only.

Where a value comes from a file, the file is named. Where I chose, the line says
**decision**. Contrast numbers were computed on 2026-10-06 with the WCAG formula.

## One look

The base look is journal-clip's "negentropic blue", from
`journal-clip/python/clip_look.py`. Clivor already copies it
(`clivor_card.py` says "journal-clip's palette"). The rack spike
(`spikes/001-suite-card-rack/rack.html`) used a second, slightly different palette.
**Decision:** the rack palette is retired, except for its four accent hues below.

## Tokens

All colour lives in one `:root` block. No colour literal appears anywhere else.

| Token | Value | Use | on BG | on PANEL |
|---|---|---|---|---|
| `--bg` | `#050509` | page | | |
| `--panel` | `#101018` | face 1 | | |
| `--void` | `#0a0a10` | face 2 (read-only) | | |
| `--line` | `#272739` | borders only | 1.39 | 1.29 |
| `--ink` | `#e7e7f2` | body text | 16.58 | 15.42 |
| `--ink-strong` | `#f4f4fb` | the question | 18.58 | 17.29 |
| `--ink-soft` | `#a7a7bd` | secondary text | 8.63 | 8.03 |
| `--ink-mute` | `#6c6c83` | decoration only | 3.98 | 3.71 |
| `--good` | `#4CAE7C` | kept, answered | 7.41 | 6.90 |
| `--warn` | `#e2a24a` | not done, caution | 9.21 | 8.56 |
| `--bad` | `#e07a7a` | refused, error | 7.01 | 6.52 |

`--bad` is the rack's red. The house palette has none.

Rules that follow from the numbers:

- `--ink-mute` is below 4.5 on every background. It never carries meaning and
  never sets text under 24 px. The lowest tone for reading is `--ink-soft`.
- `--line` is 1.3 to 1.4. It draws edges. It is never the only sign of anything.
- Everything else passes 4.5 on `--bg` and `--panel`.

## Accents

One accent per card. It tints the border, the flip button and the header name.
Nothing else.

| Card | Accent | Value | on BG |
|---|---|---|---|
| journal-clip | cyan | `#7cf7ff` | 16.09 |
| Circadia | violet | `#a78bfa` | 7.48 |
| Vej testing | gold | `#d4b23a` | 9.91 |
| Clivor | green | `#6bcf9b` | 10.68 |

Violet, gold and green are the rack's hues. Cyan is the house cyan.

**Decision:** Clivor's green sits close to `--good`. So colour is never the only
signal: every state carries a word or a mark (`kept`, `not done`, `refused`), and
the grey-scale check below must still read.

## Frame

- Portrait. Never wider than 4:5 of the slot height, full slot height, top
  centred, re-cut when the slot changes (`clip_flip.py`: `PORTRAIT = 4 / 5`).
- Face 1 is `--panel`. Face 2 is `--void`. The darker face tells the reader it is
  read-only before they read a word.
- Both faces fill the card.

## Header

`o  <card>  /  <face>` on the left, `flip` in the right corner. Same on every
face (`card-interface.md`). The card name is the switch between cards.

## Type

- Sans: `"Segoe UI", system-ui, sans-serif`. Mono: `Consolas, ui-monospace, monospace`
  (clip_look.py and rack.html agree).
- **Decision:** body 18 px at 1.5 line height (the `zig-serve` page already uses
  18 px). Secondary 15 px. The header name 14 px, mono. Nothing under 14 px.
- **Decision:** left aligned, never justified. No all-caps for more than one word.
  Short sentences, one idea per line.
- A reading font is one token, `--font-read`, defaulting to the sans stack. A web
  page cannot rely on OpenDyslexic: fonts belong to the terminal, and only the
  Bold OpenDyslexic3 and the Mono Nerd Font are installed. Set the token only
  when a proportional dyslexia font is installed.

## Motion

- Flip is a squash about the card's middle: 8 steps at 16 ms each, swap at step 4
  (`clip_flip.py`: `FLIP_STEPS = 8`, `FLIP_MS = 16`, `flip_swap_step`).
- **Decision:** with `prefers-reduced-motion`, skip the squash and swap faces at
  once. Same keys, same result.

## Focus and keys

- **Decision:** every control has a visible focus ring: 2 px `--accent`, offset
  2 px. Never `outline: none` without a replacement.
- Left and right decide, on face 1 only. Up and down flip. Left is no, right is
  yes (`card-interface.md`). Both are inert on face 2.

## Theme

**Decision:** v1 ships dark only, as journal-clip does. A light theme is not
defined and is not promised. The `zig-serve` spike page is plain light and dark
text; it is replaced by this look at build time and is not the reference.

## Procedure

Run these in order for every new or changed card.

- **Tokens.** Search the card's CSS for a colour literal outside `:root`. There
  must be none.
- **Accent.** Pick the card's accent from the table. A new card needs a new row
  here first. Do not reuse a hue.
- **Faces.** Face 1 on `--panel`, face 2 on `--void`, same header on both. Face 2
  has no decision control.
- **Contrast.** For each text and background pair the card uses, compute the
  ratio. Body text 4.5 or more. The `--ink-mute` and `--line` rules above hold.
- **Frame.** Open the card at three slot sizes: wide (1400 x 900), default
  (340 x 420), narrow (320 x 480). The card stays portrait, reaches the bottom
  of the slot, and nothing clips.
- **Motion.** Flip once normally, then once with reduced motion on.
- **Keys.** Walk the whole card with the keyboard only. Left and right do nothing
  on face 2. The focus ring is visible on every stop.
- **Grey-scale.** Take a screenshot of each face, convert to grey, and read it.
  Every state must still be told apart by its word or mark.
- **Record.** Add one line to the card's registry entry: the accent token and the
  date this procedure was run.

## Not covered

- A light theme.
- Per-card fonts or layouts. A card has an accent and its two faces. That is all
  it styles.
- Sound, haptics, touch gestures.
- Colour-blind simulation beyond the grey-scale check.
- Contrast for any pair not listed above. Compute it when a card adds one.
