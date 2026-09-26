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

