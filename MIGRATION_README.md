# LFS migration and history rewrite — short note

Summary
-------
On 2025-12-10 we performed a Git LFS migration and history rewrite on this repository to move very large binary files into Git LFS and remove them from normal Git objects. This was done to avoid GitHub's >100MB file size limit and to keep history manageable.

Key facts
---------
- Migration command used (high level):
  - `git lfs migrate import --include="venv310/**,Python-3.10.14/**,*.so,*.pt,*.onnx" --include-ref=refs/heads/main`
- Local commit mapping (examples):
  - old commit (pre-migration): `1e0170d6fa71a67912dfaf84996121d8539e49bd`
  - new commit (post-migration / current HEAD): `bb9a0d649d9ac5acee6f28385c518b309292e0b6`
- LFS objects uploaded: ~1.6 GB (many files moved to LFS)
- The rewritten `main` branch was force-pushed to `origin` after LFS upload.

Why this was necessary
----------------------
- The repository contained large files (prebuilt venvs, extracted Python source, model binaries, shared libraries) that exceeded GitHub's file size limits or made the repo impractical to clone.
- Moving these files to Git LFS keeps the repository history small and allows large binaries to be stored efficiently.

What changed
------------
- History was rewritten for `main` to replace the matching large files with LFS pointers. Commit SHAs have changed for the rewritten commits on `main`.
- A `.gitignore` file was added to prevent re-adding local venvs, extracted Python directories, compiled bytecode, and other generated/binary files.

What you must do as a collaborator
----------------------------------
If you have a local clone of this repository, do NOT try to merge the old history into the rewritten `main`. Instead follow one of these options:

Option A (recommended, destructive local update):

1. Ensure any local work is saved (create branches or patches).
2. Run:

```bash
git fetch origin
git checkout main
# Reset your local main to the new origin/main
git reset --hard origin/main
git lfs install --local
```

Option B (if you have local branches based on old commits):

1. Create a backup branch of your current work:

```bash
git checkout -b my-work-backup
```

2. Rebase your feature branch on top of the new `origin/main`:

```bash
git fetch origin
git rebase --onto origin/main <old-base> my-feature-branch
```

Notes on authentication
-----------------------
- Pushing LFS objects requires proper authentication. If you need to push LFS objects in the future, run `git lfs install` and authenticate using GitHub CLI (`gh auth login`) or a personal access token. Follow GitHub docs for `git lfs` authentication.

Additional recommendations
------------------------
- Avoid committing virtual environments, built Python distributions, or large prebuilt binaries into Git. Use `.gitignore` rules added to this repo.
- Consider storing model binaries or large artifacts in a release, artifact storage, or separate storage service if they don't need to be in the main repository.

Contact
-------
If you have questions or need help migrating your local branches, contact the repository owner or maintainers.
