# Contributing to CreatorOS

CreatorOS is the umbrella repository for architecture, canonical contracts, and repository-family verification.

## Safety boundaries

Do not commit:

- real episode scripts, manifests, analytics, or posting packages;
- narration, raw footage, rendered audio/video, licensed media, or credentials;
- secrets or environment files;
- private absolute filesystem paths.

Use clearly labeled synthetic fixtures. Human gates for claims/script, final quality, and public posting must remain false or otherwise unapproved by default.

## Change workflow

1. Add or update a focused test first and confirm that it fails for the intended reason.
2. Make the smallest implementation or contract change that passes it.
3. Run the complete test suite:

   ```sh
   python3 -m unittest discover -s tests -v
   ```

4. Verify the complete sibling workspace from this repository:

   ```sh
   python3 scripts/verify_workspace.py --repos-root ..
   ```

5. Review staged files for content, paths, media, and secrets before committing.

Contract changes must update `contracts/README.md`, preserve explicit `schema_version` semantics, and explain compatibility implications.
