# CreatorOS architecture

## Planes

```text
Content brief
    |
    v
Creator Brain <------ Creator Tool Arsenal
    |                         |
    +------ Governance -------+
    |
    v
Production Platform
    |
    v
Local Content Workspace
    |
    v
Human QC -> private upload -> publish approval
```

- **Knowledge plane:** `creator-tool-arsenal`
- **Control plane:** `creator-brain`
- **Execution plane:** `creator-production-platform`
- **Governance plane:** `creator-governance`
- **Private artifact plane:** local `workspaces/content`

## Phase 1 contracts

- `ToolRecord`: one evidence-backed tool profile.
- `ContentBrief`: requested outcome and constraints.
- `ProductionPlan`: selected tools, reasons, alternatives, and gates.
- `EpisodeManifest`: per-episode state and artifact references.
- `LicenseRecord`: rights and attribution evidence.
- `QCReport`: technical checks and unresolved human checks.

The repositories communicate through versioned files rather than importing one another's internals. Cross-repository schemas can be extracted into a dedicated contracts package only after multiple working consumers justify it.

## Human gates

```text
IDEA -> RESEARCHED -> SCRIPT_APPROVED -> ASSETS_READY -> ROUGH_CUT
-> FINAL_READY_FOR_HUMAN_QC -> HUMAN_QC -> UPLOADED_PRIVATE
-> PUBLISH_APPROVED -> PUBLISHED -> MEASURED
```

Automation may not advance `SCRIPT_APPROVED`, `HUMAN_QC`, or `PUBLISH_APPROVED`.
