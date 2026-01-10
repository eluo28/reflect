# CLAUDE.md

# Project: Reflect
**Tagline:** The Style-Cloning Video Agent
**Mission:** Automate the "rough cut" process by reverse-engineering a creator's editing signature and generating a non-destructive, professional **DaVinci Resolve timeline (.otio)** for manual refinement.

---

## 1. System Overview & Core Philosophy

**Reflect** is a **heuristic cloning engine** that integrates directly into professional NLE (Non-Linear Editor) workflows. It operates on the principle that editing consists of two types of material:
1.  **Solids (Dialogue):** Fixed duration, semantic content.
2.  **Liquids (B-Roll):** Flexible content that can be time-warped to fill gaps.

**The Output Strategy:**
Reflect does **not** render video. It calculates the mathematically perfect edit and saves it as an **OpenTimelineIO (.otio)** file. The user imports this into DaVinci Resolve to see the timeline instantly, retaining full creative control to tweak cuts, color grade, or adjust audio.

---

## 2. Architecture: The 4-Service Pipeline

The system is composed of four distinct, decoupled services.

### Service A: StyleExtractor
* **Goal:** Reverse-engineer the "rules" of the user's style from a previous project.
* **Input:** A reference `.otio` (OpenTimelineIO) file exported from DaVinci Resolve.
* **Analysis:**
    * **Pacing:** Average shot duration (e.g., 3.2s).
    * **Rhythm:** Do cuts align with Beats, Bars, or Onsets?
    * **Structure:** How is B-roll interleaved with Dialogue?
* **Output:** `style_profile.md` (Natural language constraints + weights).

### Service B: AssetAnnotator
* **Goal:** Pre-process raw footage into queryable metadata.
* **Operation:** Runs three analysis modules on every raw file:
    1.  **The Ear (Faster-Whisper):** Transcribes text + timestamps. Identifies "Semantic Valid Ranges" (start/end of actual speech).
    2.  **The Eye (OpenCV):** Calculates the **"Tripod Score"** (High Sharpness / Low Motion) to find stable, non-blurry windows.
    3.  **The Metronome (Librosa):** Analyzes the background music to generate a `Beat Grid` and `Onset Grid`.
* **Output:** `manifest.json`.

### Service C: EditPlanner (Agentic Workflow)
* **Goal:** Solve the timeline puzzle.
* **Logic:**
    1.  **Place Solids:** Arranges dialogue clips in narrative order with style-defined padding.
    2.  **Calculate Gaps:** Measures silence between dialogue blocks.
    3.  **Pour Liquids:** Allocates B-roll clips to gaps based on semantic relevance.
    4.  **Elastic Time:** Calculates the `Speed Factor` needed to make the B-roll exactly fill the musical measure.
* **Output:** An internal `Timeline Blueprint`.

### Service D: The Exporter ("The Conform")
* **Goal:** Translate the Agent's blueprint into industry-standard exchange format.
* **Operation:** Maps the internal timeline objects to the OpenTimelineIO schema, ensuring absolute file paths are preserved for DaVinci Resolve linking.
* **Output:** `final_edit.otio`.

---

## Code Style

- You are a staff software engineer that writes clean, modular, easy to understand code
- Write clean, concise code - prioritize readability (code should be immediately understandable)
- Use type hints for all arguments and return values (strict Pyright configuration enforced)
- Prefer clear naming over explanatory comments
- Reference pyproject.toml for linter rules
- Import at the top of files, not within functions
- Use BaseReflectModel for all Pydantic schemas
- StrEnum should use auto() for enum values where possible
- Do NOT use tuples, use Pydantic models instead
- Reference code from surrounding files for convention
- Build all schemas in a schemas folder in the folder of the service that uses them
- Avoid `Any` type where possible
- NEVER use async code
- NEVER ignore lint errors, either fix or ask the user how to proceed forward if you can figure out how to fix

**Service Class Development:**
- Never expose database models directly - wrap in schema types
- Provider function in `providers.py` (use `@cache` for singletons)

