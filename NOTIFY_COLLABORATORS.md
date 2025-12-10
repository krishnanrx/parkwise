# Announcement: Git LFS migration (2025-12-10)

Summary
-------
On 2025-12-10 we performed a Git LFS migration and history rewrite for `main` to move large files into Git LFS and keep the repository history lean.

What you should do now
----------------------
1. Read `MIGRATION_README.md` and `CHANGELOG.md` for the full details and commit mapping.
2. To sync your local clone (destructive, recommended):

```bash
git fetch origin
git checkout main
git reset --hard origin/main
git lfs install --local
```

3. If you have local branches based on the old history, back them up and rebase onto `origin/main`.

Notes
-----
- The rewritten migration commit is `bb9a0d649d9ac5acee6f28385c518b309292e0b6`.
- A `migration-2025-12-10` tag has been created for easy reference.

If you'd like me to open a GitHub issue or create a PR notifying collaborators, tell me and I can (requires GitHub API/CLI authentication).
