# Git Submodule Usage Guide

This project uses Git submodules to manage two external components.

## Submodule List

| Submodule | Repository | Purpose |
|-----------|-----------|---------|
| qduoj | https://github.com/QingdaoU/OnlineJudgeDeploy.git | OJ system deployment config |
| fps-problems | https://github.com/zhblue/freeproblemset.git | FPS problem set (609 problems) |

## Initial Clone

```bash
# Clone with all submodules
git clone --recursive git@github.com:guancyxx/cdut_stu_agents.git

# Or, if already cloned
git clone git@github.com:guancyxx/cdut_stu_agents.git
cd cdut_stu_agents
git submodule update --init --recursive
```

## Update Submodules

### Update all submodules to latest

```bash
git submodule update --remote --merge
```

### Update a specific submodule

```bash
# Update qduoj
git submodule update --remote qduoj

# Update fps-problems
git submodule update --remote fps-problems
```

### Pull updates for main repo and submodules

```bash
# Pull main repo updates
git pull

# Sync submodules to the commit specified by main repo
git submodule update --init --recursive
```

## Check Submodule Status

```bash
# View all submodule statuses
git submodule status

# View latest commit for each submodule
git submodule foreach git log --oneline -1
```

## Notes

### 1. Submodule working directories are independent
- Once inside a submodule directory, it is an independent git repo
- Changes inside a submodule do not automatically affect the main repo

### 2. Modifying submodule content

```bash
# Enter the submodule
cd qduoj

# Check current branch (usually detached HEAD)
git branch

# Switch to main branch for development
git checkout main

# Make changes, commit
git add .
git commit -m "description of changes"

# Return to main repo
cd ..

# Update the submodule reference in main repo
git add qduoj
git commit -m "update qduoj submodule reference"
```

### 3. Sync submodules when switching branches

```bash
# Switch branch
git checkout <branch-name>

# Sync submodules (important!)
git submodule update --init --recursive
```

## Common Issues

### Issue: Submodule directory is empty

```bash
# Initialize and update all submodules
git submodule update --init --recursive
```

### Issue: Submodule in detached HEAD state

This is normal. Submodules default to pointing at a specific commit, not a branch. To modify:

```bash
cd <submodule-directory>
git checkout main  # or other branch
```

### Issue: Remove a submodule

```bash
# 1. Remove from .gitmodules
git config -f .gitmodules --remove-section submodule.<submodule-name>

# 2. Remove from .git/config
git config -f .git/config --remove-section submodule.<submodule-name>

# 3. Remove from staging
git rm --cached <submodule-path>

# 4. Delete the physical directory
rm -rf <submodule-path>
rm -rf .git/modules/<submodule-name>

# 5. Commit the change
git commit -m "remove submodule <submodule-name>"
```

## References

- [Git Submodules Official Documentation](https://git-scm.com/book/en/v2/Git-Tools-Submodules)
- [QDUOJ Documentation](https://github.com/QingdaoU/OnlineJudge)