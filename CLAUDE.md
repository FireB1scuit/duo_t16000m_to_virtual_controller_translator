# Project instructions

## Git workflow

- Commit and push to `origin` regularly as work progresses in this repo — don't let changes pile up uncommitted across a session.
- Standing authorization: `git add`, `git commit`, and `git push` to `origin main` (or the current branch's tracked remote) do NOT require asking for confirmation first. This overrides the default "ask before pushing" rule for this project only.
- Still never force-push, rewrite history, or push to a branch other than the one currently checked out without asking first.
- Before committing, briefly review `git status`/`git diff` for anything that looks like a secret or credential before staging it.
- Follow the rebuild-the-exe rule noted in memory: rebuild the packaged `.exe` at the end of every response that touches the code, and include the resulting build artifacts change (if tracked) in the same commit when relevant.
