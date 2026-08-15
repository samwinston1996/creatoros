# CreatorOS contracts

This directory is the canonical Phase 1 contract reference for the CreatorOS repository family. Sibling repositories may maintain implementation-local copies while consumers stabilize; behavioral changes must be reflected here first and versioned deliberately.

## Schemas

| Contract | File | Producer / consumer |
|---|---|---|
| `ToolRecord` | `schemas/tool-record.schema.json` | Tool Arsenal / Brain |
| `ContentBrief` | `schemas/content-brief.schema.json` | Content Workspace / Brain |
| `ProductionPlan` | `schemas/production-plan.schema.json` | Brain / Production Platform |
| `EpisodeManifest` | `schemas/episode-manifest.schema.json` | Content Workspace / Production Platform |
| `LicenseRecord` | `schemas/license-record.schema.json` | Governance / Production Platform |
| `QCReport` | `schemas/qc-report.schema.json` | Production Platform / Governance |

All examples are synthetic, use `schema_version` `1.0.0`, and leave human approvals unset or false. Contract fixtures must never include real episode material, credentials, licensed assets, or private absolute paths.

## Compatibility

- Additive optional fields are backward-compatible within `1.x`.
- Removing fields, changing meanings, or tightening accepted values requires a new major schema version.
- Human gates for claims/script, final quality, and public posting cannot default to approved.
- Run `python3 -m unittest discover -s tests -v` and the workspace verifier before proposing a contract change.
