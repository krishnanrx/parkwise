# Changelog

## 2025-12-10 — Git LFS migration and history rewrite

Summary
-------
This entry documents the Git LFS migration and the mapping of important commit SHAs so collaborators can reconcile local branches.

Commit mapping (important points)
---------------------------------
- Pre-migration remote `origin/main` (before rewrite):
  - 238233ba1c9832fd4c40e2051fb4fcbfff291710
- A local pre-migration commit that was present before the migration:
  - 1e0170d6fa71a67912dfaf84996121d8539e49bd
- Post-migration rewritten `main` (result of `git lfs migrate import`):
  - bb9a0d649d9ac5acee6f28385c518b309292e0b6
- Follow-up commit adding `.gitignore` and `MIGRATION_README`:
  - 71debaa28446aba87218d82ff6cb5f348af39b26

What happened
-------------
- We ran `git lfs migrate import` to move large files (patterns such as `venv310/**`, `Python-3.10.14/**`, `*.so`, `*.pt`, `*.onnx`) into Git LFS and rewrote history on `main`.
- LFS objects (~1.6 GB total) were uploaded and the rewritten `main` branch was force-pushed to `origin`.

Impact for collaborators
------------------------
- Because history was rewritten, local clones with the old history must update carefully. Do NOT merge the old `main` into your branches.
- Recommended quick sync (destructive reset):

```bash
git fetch origin
git checkout main
git reset --hard origin/main
git lfs install --local
```

If you have local branches based on old commits, create backups and rebase them onto the new `origin/main`.

Notes
-----
- We added a `.gitignore` to help prevent future accidental commits of virtualenvs, extracted Python directories, and compiled artifacts.
- If you need assistance migrating any local branches, open an issue or contact the repository maintainers.
