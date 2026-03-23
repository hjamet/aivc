# Phase 9 — Global CLI Exposure

## 1. Context & Discussion (Narrative)
> The user was unable to run the `aivc web` command after installation (`command not found`).
- Asynchronous analysis via the Architect role revealed that the `install.sh` and `install_dev.sh` scripts correctly installed the package in an isolated virtual environment via `uv`, but the venv's `bin` folder was not globally exposed in the user's `$PATH`.
- The approved architectural decision was to add a symbolic link (`symlink`) creation step to the `~/.local/bin/aivc` path at the end of installation, so the CLI is easily accessible without further effort.

## 2. Concerned Files
- `install.sh`
- `install_dev.sh`
- `README.md`

## 3. Objectives (Definition of Done)
- At the end of the installation scripts, a `~/.local/bin/aivc` symbolic link must point back to the native `aivc` executable located in the respective venv (prod or dev).
- Backward compatibility ensured (`mkdir -p` of `~/.local/bin` if non-existent).
- `README.md` is updated (Roadmap & Index section).
