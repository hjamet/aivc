# 👋 Handover: Project Internationalization & English Transition

## Context & Discussion
The project AIVC (AI Version Control) has undergone a full internationalization process to facilitate collaboration with English-speaking contributors, specifically **Amir**. 

Initially documented and commented in French, the entire ecosystem is now transitioned to English. This includes:
*   The main **README.md**.
*   All technical documentation files in the `docs/` folder.
*   The entire task roadmap and all historical task specifications in `docs/tasks/`.
*   All docstrings and technical comments within the source code (`src/aivc/`) and utility scripts (`scripts/`).
*   The system prompt used by the MCP server to guide AI agents.

The core functionality of AIVC remains unchanged: it provides a versioned long-term memory for AI agents by snapshotting files during "commits" accompanied by detailed Markdown notes. These notes are the primary target for semantic search, while the files themselves provide the specific code/content context.

## Decisions & Key Points
*   **High Fidelity Translation**: Every document has been translated with a focus on preserving all technical details and architectural context. No information has been omitted.
*   **Natural Language**: The translation aims for natural English while staying as close to the original meaning as possible.
*   **Source Code Purity**: All French docstrings and internal comments have been replaced with English equivalents.
*   **MCP System Prompt**: The built-in instructions for AI agents (the `_SYSTEM_PROMPT` in `server.py`) are now fully in English to ensure clear guidance for international LLMs.
*   **Roadmap Synchronization**: The Roadmap in the `README.md` now points directly to the English versions of the task specifications.

## Mission for the Next Agent
The project is now ready for English-speaking collaboration. The main objective moving forward is to continue the development of AIVC features while maintaining documentation and code comments in English only.

> **⚠️ ATTENTION: Do NOT start coding directly. BEFORE ANYTHING ELSE, perform at least 3 semantic searches (`search_memory` or `semsearch`) to explore the codebase and understand the scope. Then, establish a clear IMPLEMENTATION PLAN and submit it to the user. Discuss any ambiguous details BEFORE touching anything.**

> **📋 A task specification file exists for the current overarching goal: `docs/tasks/internationalization_and_english_docs.md`. Read it first before starting your plan.**

**Current Focus**: Phase 19 (Web Dashboard UX) is the latest technical development. Ensure that any future UX or backend changes respect the now-established English-only standard.
