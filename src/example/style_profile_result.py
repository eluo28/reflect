# ruff: noqa
"""Style profile analysis result."""

style_profile_analysis = """**Editing Style Profile – “Unnamed” 60 fps Timeline (205 s)**  

---  

### 1. Pacing  

| Metric | Value | Interpretation |
|--------|-------|------------------|
| **Average shot length** | **4.29 s** | On the surface the edit looks “moderate” – long enough to read a quick caption or hear a sound bite, but the average is pulled up by a few very long holds. |
| **Median shot length** | **0.78 s** | More than half of the cuts are under one second – the real “working” pace is **rapid**. |
| **Standard deviation** | **12.26 s** | Very high variance; the edit swings between flash‑cut fragments and extended takes. |
| **Very short cuts (< 0.5 s)** |≈ 30 % of clips (≈ 35 of 117) – the sample of the first 10 clips are all under 0.5 s. | Creates a jittery, high‑energy feel typical of jump‑cut montages. |
| **Long holds (> 5 s)** | ~ 8 % of clips (≈ 9 of 117) – includes a 5.85 s fragment and a 110.52 s master‑shot. | Provides occasional breathing room for narration, landscape or “talk‑to‑camera” moments. |

**What it suggests:** The timeline is **fast‑paced overall**, with a dominant rhythm of sub‑second slices that keep the viewer’s attention ticking, punctuated by a handful of longer shots that act as anchors or emotional beats.

---  

### 2. Rhythm & Structure  

| Aspect | Detail |
|--------|--------|
| **Track distribution** | - **Video Track 0:** 10 clips (≈ 8 % of video material) – a short “intro” lane. <br>- **Video Track 1:** 94 clips (≈ 92 %) – the main storyboard. |
| **Gap frequency** | 12 gaps total – a **gap‑to‑clip ratio of 1 gap per 9.8 clips**. <br>Average gap length **26.5 s**, far longer than the typical cut. Gaps are clustered on the audio tracks (9 gaps on Audio 2). |
| **Silence / pause handling** | Gaps are largely on the audio side, indicating intentional pauses (e.g., “beat” for voice‑over, B‑roll silence, or music breaks). No visual black‑frames are inserted as gaps on the video tracks. |
| **Transitions** | **0** – the edit relies exclusively on straight cuts. No dissolves, wipes or motion‑based transitions are used. |
| **Implication for rhythm** | The piece runs like a **cut‑driven montage**: rapid visual succession, occasional long‑hold beats, and intentional audio pauses that function as narrative punctuation rather than visual fades. |

---  

### 3. Technical Style  

| Metric | Value | Comment |
|--------|-------|---------|
| **Clips with effects** | **44.4 %** (≈ 52 of 117) | Almost half the cuts carry a visual effect (color‑grade tweak, speed‑ramp, glitch, etc.). The editor leans heavily on stylisation to differentiate each micro‑clip. |
| **Source‑trim usage** | Roughly **20 %** of clips start from a non‑zero in‑point (e.g., “from 31.2 s”, “from 0.4 s”). The remaining ~80 % are inserted from the clip’s start (0.0 s), implying that many are used as whole‑clip “stingers” rather than surgically trimmed. |
| **Multi‑track complexity** | - **2 video tracks**: one thin “intro” lane, one dense primary lane.<br>- **2 audio tracks**: one for music/dialogue (3 clips, 1 gap) and a second for sound‑effects/ambient layers (10 clips, 9 gaps).<br>- No nesting or sub‑mixes reported. | The layout is **simple but purposeful**: visual material on a single dominant track, audio layered to create rhythmic beats and occasional silence. |
| **Overall technical footprint** | The edit is **effect‑rich yet structurally straightforward**, with a clear hierarchy (primary video track → audio layers). |

---  

### 4. Overall Editing Signature  

The creator’s edit reads as a **high‑energy montage/vlog hybrid**: sub‑second jump cuts dominate, giving the piece a kinetic, “scroll‑through” vibe, while the occasional long‑duration B‑roll or talking‑head shot provides narrative grounding. The heavy reliance on visual effects (≈ 44 %) adds a modern, stylised texture, and the lack of transitions forces each cut to feel decisive. Audio gaps are used deliberately to create spoken‑word beats or musical rests, reinforcing the rhythmic pulse.

**Distinctive patterns / preferences**  

* **Micro‑cut emphasis:** ~30 % of cuts are under 0.5 s, which is higher than typical vlog or documentary edits.  
* **Effect‑driven differentiation:** Almost half the clips are effect‑tagged, suggesting the editor’s signature is to give each fragment a visual “stamp”.  
* **Sparse transition palette:** Zero dissolves – the edit trusts pure cuts and timing for flow.  
* **Two‑track visual hierarchy:** A thin intro lane (10 clips) followed by a dense main lane (94 clips) – a typical “cold‑open → main‑story” structure.

**Style classification:** **Fast‑paced, effect‑rich montage** (often seen in YouTube travel/vlog compilations, social‑media highlight reels, or promotional lookbooks).  

---  

### 5. Replication Guidelines for an AI Editor  

1. **Shot Length Logic**  
   * Sample a **log‑normal distribution** with median ≈ 0.8 s, mean ≈ 4.3 s, and a long tail up to ~110 s.  
   * Force **≈ 30 %** of generated cuts to be **≤ 0.5 s**; insert **≈ 8 %** of clips **≥ 5 s** for narrative beats.

2. **Track Layout**  
   * Create a **primary video track** holding ~90 % of cuts; optionally add a short intro track (≈ 10 % of clips).  
   * Place **audio music/voice‑over** on one track; distribute **sound‑effects** on a second audio track with many short silences (≈ 9 % gaps, avg ≈ 26 s).

3. **Transitions & Gaps**  
   * Use **straight cuts only** – no dissolves or wipes.  
   * Insert **audio gaps** of 20‑30 s at logical narrative pauses (e.g., before a long‑hold B‑roll or after a segment).  

4. **Effects Application**  
   * Randomly tag **≈ 45 %** of clips with a visual effect (color‑grade bump, speed‑ramp, glitch, vignette).  
   * Keep **effect intensity modest**; the goal is differentiation, not dominance.

5. **Source Trimming**  
   * For **~80 %** of clips, start from the source‑clip’s beginning (0 s).  
   * For the remaining **~20 %**, offset the in‑point by a random value (0.3‑5 s) to simulate selective trimming.

Following these parameters will reproduce the creator’s signature **rapid‑cut, effect‑laden montage** with the same rhythmic balance of micro‑snippets, occasional long holds, and strategically placed audio silences."""
