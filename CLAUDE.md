# CLAUDE.md

# Project: Reflect

**Tagline:** The Style-Cloning Video Editing Agent

**Mission:** Automate the "rough cut" process by reverse-engineering a creator's editing signature and generating a non-destructive, professional **DaVinci Resolve timeline (.otio)** for manual refinement.

## Monorepo Structure

```
reflect/
├── backend/          # FastAPI + Python pipeline services
├── frontend/         # React + Vite + Tailwind UI
├── scratch_examples/ # Development test files
└── Makefile
```

See `backend/CLAUDE.md` for backend-specific code style and conventions.

## Quick Start

```bash
make install    # Install all dependencies
make backend    # Start backend (in terminal 1)
make frontend   # Start frontend (in terminal 2)
```

MongoDB Atlas connection is configured in `backend/.env`.

## Architecture: The 4-Service Pipeline

1. **StyleExtractor** - Reverse-engineer editing style from reference `.otio` files
2. **AssetAnnotator** - Analyze footage (speech, stability, music beats)
3. **EditPlanner** - Solve the timeline puzzle using AI agents
4. **EditExecutor** - Generate final `.otio` file for DaVinci Resolve

## Core Philosophy

Reflect operates on the principle that editing consists of:
- **Solids (Dialogue):** Fixed duration, semantic content
- **Liquids (B-Roll):** Flexible content that can be time-warped to fill gaps

Reflect does **not** render video. It calculates the edit and saves it as an **OpenTimelineIO (.otio)** file for import into DaVinci Resolve.
