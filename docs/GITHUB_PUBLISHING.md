# Publishing RepoFlow to GitHub

Recommended repository name:

```text
repoflow
```

Recommended description:

```text
A lightweight Git and GitHub desktop client for Linux/KDE focused on simple staging, commits, sync, and repository management without the terminal.
```

Use the source folder itself as the Git repository. Do not publish the installed runtime under `~/.local/share/repoflow`.

Suggested local path:

```text
~/Projects/RepoFlow
```

Initialize and create the first commit:

```bash
cd ~/Projects/RepoFlow
git init -b main
git add .
git commit -m "feat: bootstrap RepoFlow v0.2.3 with core Git and GitHub workflows"
```

After creating an empty GitHub repository named `repoflow`:

```bash
git remote add origin https://github.com/<YOUR_USERNAME>/repoflow.git
git push -u origin main
```

Do not initialize the remote repository with a README, `.gitignore`, or license if the local source folder already contains the initial history.
