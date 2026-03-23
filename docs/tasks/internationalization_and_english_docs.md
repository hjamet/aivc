# Internationalization and English Documentation 🇬🇧

## 1. Context & Discussion (Narrative)
> *The arrival of Amir, an English-speaking Iranian collaborator, requires the project to step out of its French-speaking bubble.*
The AIVC project was initially designed and documented in French. To enable smooth collaboration, it is crucial that all documentation (README, guides, task specifications) and code metadata (docstrings, complex comments) be in English. This ensures that any international contributor can understand not only how to use the tool, but also how it is built and what past architectural decisions were made.

## 2. Concerned Files
- `README.md` (High Priority)
- `docs/**/*` (Index and task specifications)
- `src/aivc/**/*.py` (Source code and docstrings)
- `scripts/*.py` (Utilities)

## 3. Objectives (Definition of Done)
- [x] `README.md` is entirely in English, including the Roadmap and Description sections.
- [x] All documentation indexes in `docs/` are in English.
- [x] All past task specifications (Phases 1 to 19) in `docs/tasks/` are translated.
- [x] Source code no longer contains French docstrings or comments.
- [x] The roadmap in `README.md` points to the translated versions of tasks.
- [x] A context handover (Handover) is generated in English for Amir.
