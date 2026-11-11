# Anchor Task Definition: Recursive Intent Resolution

## Purpose
To serve as the primary trace point for the Unified Map. This task maps how a high-level human intent is decomposed, scored, executed, and refined.

## Workflow Trace
1. **Interface**: Capture `UserIntent` via the doctrine of "Emergent Context".
2. **Core**: Decompose `UserIntent` into `SemanticQuanta` using `AGPIAI-3.0` schemas.
3. **Engine**: Execute `SemanticQuanta` within `Sovereignty` bounds.
4. **Prototype**: Perform the actual work (e.g., file edit, DB query).
5. **Feedback**: Return `FidelityScore` and `StateUpdate` to the Core for loop closure.

## Inputs
- `raw_prompt`: String (Natural Language)
- `context_snapshot`: JSON (Current system/repo state)

## Outputs
- `action_plan`: List[AtomicAction]
- `fidelity_score`: Float (0.0 - 1.0)
- `loop_status`: Enum (CONTINUE, COMPLETE, FAIL)
