# RepoFlow Manual QA Checklist

RepoFlow is validated incrementally before new features are added. Use a disposable repository such as `~/Documents/RepoFlow-QA`; do not use an important project for destructive or divergence tests.

## Local core gate

- T01 KDE launcher startup
- T02 repository persistence
- T03 last repository persistence
- T04 initialize existing folder
- T05 reopen repository
- T06 remove/re-add shortcut without deleting repository
- T07 untracked status
- T08 stage checkbox
- T09 unstage checkbox
- T10 untracked file preview
- T11 first commit
- T12 modified file diff
- T13 commit with no staged files is rejected
- T14 commit without message is rejected
- T15 partially staged file is represented accurately
- T16 multiple commits before push
- T17 history persistence
- T18 create branch
- T19 switch branch

## T15 expected behavior in v0.2.3

1. Start from a clean committed `README.md`.
2. Add `VERSION A` and save.
3. Refresh RepoFlow and check `README.md` to stage it.
4. Without committing, add `VERSION B` and save.
5. Refresh RepoFlow.

Expected:

```text
◩ README.md    Modified · Partially staged
```

The diff panel must contain two sections:

```text
STAGED CHANGES
+VERSION A

UNSTAGED CHANGES
+VERSION B
```

`VERSION B` must not appear as an added line in the staged diff.

Checking the partially staged file should stage the complete current file. Unchecking it should unstage the complete file.

## GitHub integration gate

After T01-T19 pass, continue with:

- invalid token handling
- valid GitHub authentication
- account persistence / session-only fallback
- disconnect
- repository browser and search
- create GitHub repository
- auto-connect `origin`
- first push/upstream
- multiple-commit push
- fetch and behind count
- fast-forward pull
- diverged-history protection
- clone from account
- private HTTPS clone
- clone from URL
- existing destination rejection
- manual remote connection/update
- network failure handling
- token leakage checks
- full restart smoke test

## T18-T19 branch regression (v0.2.4)

### T18 — Create and switch branch

1. Start on `main`.
2. Click the branch button, then `+ New Branch`.
3. Enter `feature/qa-test`.
4. Click `Create and Switch`.
5. PASS when the header changes to `feature/qa-test`, the status bar confirms the switch, and the branch menu lists both `main` and `feature/qa-test`.

### T19 — Switch between existing branches

1. From `feature/qa-test`, open the branch menu and choose `main`.
2. PASS when the header changes to `main`.
3. Switch back to `feature/qa-test`, then finally return to `main`.
4. PASS when every switch updates both the header and checked branch menu entry.


## GitHub authentication regression (T20)

1. Open **GitHub → Account**.
2. Enter an intentionally invalid token such as `invalid-token-repoflow-test`.
3. Click **Connect**.
4. Expected: a **GitHub Authentication Failed** dialog appears, the sidebar remains **Connect GitHub**, and the application stays responsive.
5. The log should contain `GitHub authentication failed` and the background task lifecycle.



## v0.2.8 QA-polish smoke tests

- **T51 — First-push upstream:** first push from a repository with `origin` but no upstream must establish `origin/main`.
- **T52 — Already-up-to-date feedback:** Pull on an up-to-date repository must leave a visible `Already up to date.` status message.
- **T53 — Binary preview:** selecting an untracked or staged binary file must never dump raw bytes into the diff viewer.
- **T54 — Activity indicator:** clone/fetch/pull/push must show the status-bar activity indicator until the worker finishes.
- **T55 — Commit-and-push label:** button text must render as `Commit and Push` with no mnemonic underscore.
- **T56 — Application icon:** KDE launcher and RepoFlow window must use `assets/repoflow.svg`.


## v0.3.0 Stage 3 safety smoke tests

- **T57 — Sensitive-file review:** create an untracked `.env`; checking it must open Safety Review before staging. Cancel must leave it unstaged.
- **T58 — Add risky file to `.gitignore`:** repeat T57 and choose **Add to .gitignore**. `.env` must disappear from normal untracked changes and `.gitignore` must contain `/.env`.
- **T59 — Stage Anyway:** create another risky file such as `test-key.pem`, choose **Stage Anyway**, and verify it stages normally. Unstage it afterward unless it is intentionally part of the test repository.
- **T60 — `.gitignore` manager:** open **Repository → Manage .gitignore…**, add a harmless test rule or preset, save, and verify `.gitignore` becomes a normal repository change.
- **T61 — Large-file review:** create a sparse/local test file above 25 MiB; staging must show a Large file warning instead of staging silently. Remove the file after the test.
- **T62 — Conflict safety banner:** open a repository with an externally-created unresolved merge conflict. RepoFlow must show the conflict banner and disable Pull/Push while allowing the conflict file to be staged after manual resolution.
- **T63 — Divergence safety banner:** after Fetch produces both ahead > 0 and behind > 0, RepoFlow must show the divergence banner and disable Pull/Push while keeping Fetch available.
- **T64 — Regression:** restart RepoFlow and confirm GitHub persistence, normal staging, commit, fetch/pull/push, branch switching, binary preview, and background progress from v0.2.8 still work.
