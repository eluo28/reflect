# Reflect

**The Style-Cloning Video Editing Agent**

> Built for the [Cerebral Valley Agentic Orchestration Hackathon](https://cerebralvalley.ai/e/agentic-orchestration-hackathon/details)

---

## What is Reflect?

Reflect is an AI-powered system that automates the "rough cut" video editing process. Instead of manually scrubbing through hours of footage, creators upload their raw clips and Reflect generates a professional timeline ready for refinement.

**Key insight:** Reflect doesn't render video. It produces an industry-standard **OpenTimelineIO (.otio)** file that imports directly into DaVinci Resolve, Premiere Pro, or any NLE that supports OTIO.

---

## How It Works

```
Raw Footage + Music  →  AI Analysis  →  Timeline Blueprint  →  .otio Export
```

1. **Upload** your video clips and background audio
2. **Optionally** provide a reference edit to clone its style
3. **Generate** — AI agents analyze footage, plan cuts, and build the timeline
4. **Download** the .otio file and import into your editor for final touches

---

## The Pipeline

Reflect orchestrates four AI-powered services:

| Stage | Service | What It Does |
|-------|---------|--------------|
| 1 | **Asset Annotator** | Analyzes footage for speech, stability, and musical beats |
| 2 | **Style Extractor** | Learns editing patterns from reference timelines |
| 3 | **Edit Planner** | AI agents determine cuts, pacing, and clip selection |
| 4 | **Edit Executor** | Converts the plan into a valid .otio timeline |

---

## Tech Stack

- **Backend:** Python, FastAPI, OpenAI Agents, MongoDB Atlas
- **Frontend:** React, TypeScript, Tailwind CSS, Vite
- **Media:** OpenTimelineIO, FFmpeg, librosa, faster-whisper

---

## Quick Start

```bash
# Install dependencies
make install

# Start backend (terminal 1)
make backend

# Start frontend (terminal 2)
make frontend
```

Requires: Python 3.11+, Node.js 18+, MongoDB Atlas connection string, OpenAI API key

---

## Why OTIO?

OpenTimelineIO is an open standard for editorial timelines. By outputting .otio instead of rendered video, Reflect:

- Preserves full editing flexibility
- Keeps source media at original quality
- Integrates with professional workflows
- Lets creators refine AI decisions, not fight them

---

## License

MIT
