# DRIFT — the thesis of the whole app

Sesefus exists to give a person **control over their drift** — to see it,
and to correct the parts they choose. Every module in this repo is a sensor
or an actuator for one form of drift. None of it is outside this frame.

## The six drift forms

| Drift form | Theoretical (inferred / intended) | Actual (observed) | Instrument in repo |
|---|---|---|---|
| Circadian | rhythm schedule, alarm profiles | when you actually wake, wind down, respond | Circadia / alarm engine (`core/`) |
| Emotional | personal baseline (EMA of valence/arousal/salience) | today's scored memo | ETDI pipeline (`tools/etdi_*`) |
| Temporal-perceptual | clock time | how time felt (distortion likelihood) | ETDI's distortion axis |
| Semantic | your archived thinking (vector shards) | what you're saying/thinking now | sieve → forge → vector search |
| Behavioral | stated intentions, scheduled day | what you actually did | image sieve + memo metadata |
| Moral / practical | chosen virtues | conduct under review | Stoic daily reflection (`ssfs stoic`) |

The Stoic evening review — Seneca's nightly audit — is drift measurement,
practiced for two thousand years without the math. This app instruments an
ancient loop; it does not invent one. That is the honest Sisyphus flip: the
boulder never stays up, correction is the daily task, and the app's job is
making the daily return light instead of punishing.

## The shared loop

Every drift form reduces to the same four steps:

```
1. instrument records ACTUAL          (memo, screenshot, timestamp, alarm ack)
2. baseline infers THEORETICAL        (EMA over your own history: s̄ₜ = η·s̄ₜ₋₁ + (1−η)·sₜ)
3. normalized residual = DRIFT        (δ = actual − s̄ ;  D = ‖δ/σ‖ per-axis, σ from MAD)
4. surface + gentle correction cue    (flag, alarm, reflection prompt — never a verdict)
```

Step 3 is the Euclidean norm applied to a residual in a space normalized by
your own variability — diagonal Mahalanobis distance. Two properties matter:

- **It degrades gracefully.** With no history (s̄ = 0, σ = 1) it collapses to
  the plain state magnitude √(V² + A² + S²). Day one, the system measures
  distance-from-neutral; as memos accumulate it smoothly becomes
  distance-from-*you*.
- **Thresholds become personal.** A flag at D > τ means "a τ-sigma day for
  you," not an absolute constant that over-flags volatile people and never
  fires for flat ones.

This is the RSDC engine (Neurialab, `Recursive Semantic Drift Correction`)
translated honestly: EMA baseline + deadband + norm of the drift vector.
Its eq. 4 is an EWMA control chart's tracking signal — a mechanism with
fifty years of statistical process control behind it. RSDC is not a side
paper; it is the core loop, and each module is a different sensor feeding it.

## Behavioral drift — the newest sensor

The image sieve (`shredder/image_sieve.py`) is the behavioral-drift
instrument: screenshots are the record of what you actually did; schedules
and stated intentions are the theoretical. Computable signals, cheapest first:

1. **Cadence drift** — scheduled journal time vs actual entry timestamps.
   An EMA of your entry hour; deviation measured in your own σ. The data
   already exists in the manifests.
2. **Attention drift** — the sieve's `concepts` tags form a weekly histogram
   of what you actually worked on; divergence from your trailing baseline
   (cosine or KL) says your hands have wandered from what your mouth said
   mattered.
3. **Follow-through drift** — tasks stated in memos (`derived.tasks`) vs later
   evidence of them in screenshots or subsequent memos. Hardest; build last.

## Design stance (the line that keeps this out of the therapy-app trap)

**Not all drift is error. Some drift is growth.** RSDC itself encodes this:
η < 1 on purpose — plasticity is a feature, identity is not frozen. A tool
that treats every deviation from baseline as a fault becomes a nagging
machine. The product stance:

> The app measures and shows. The user decides which drift is a bug and
> which is becoming someone new.

Correction cues are invitations (an alarm, a reflection prompt, a flag on a
chart), never verdicts. This is also the branding sidestep: sesefus is a
drift instrument — a cognitive prosthetic — not a mental-health product.

## Implementation ladder

- **v1 (built)** — ETDI state metric per memo; fixed flag threshold 0.15;
  screenshots → embeddable abstract-notion chunks.
- **v2 (next)** — the drift layer in `etdi_store.py`: `s̄`/`σ` columns per
  axis, drift D computed at score time, flag layer reads D > τ instead of
  raw ETDI. Candidate formula switch: ETDI state = √(v²+a²+s²)/(√3·min).
- **v3 (later)** — cross-domain drift dashboard: one panel per drift form,
  same normalization everywhere; attention drift from screenshot concepts;
  calibration drift (model-inferred vs self-reported — the same math watching
  the *model* instead of the person).

---

One sentence, for whenever it's needed:
**Neurialab builds drift-correction instruments; sesefus is the first.**
