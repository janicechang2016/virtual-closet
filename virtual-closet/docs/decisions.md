# Decision log

## 2026-07-11 — Avatar lock DEFERRED; flow-first, credit-conscious

**Decision (user):** Stop spending fal credits on avatar perfection for now. Build the closet app flow (Phase 4, $0) first; lock avatar-v1 later. Round-2 candidates (`avatar/versions/r2_candidate_*.png`) are all QA-clean and retained; `r2_candidate_2` (best persona face) serves as **provisional draft avatar** for UI development — it is NOT locked, and no renders against it are canon.

**Standing rule from this decision:** API-spending actions (any fal call) happen only in explicit, user-approved batches. The app's generate path ships **disabled by default** (`ENABLE_GENERATION` env flag) with copy-prompt mode as the $0 fallback.

## 2026-07-11 — Avatar identity: AI persona face + real body proportions

**Decision (user):** The three face reference photos are AI-generated persona images (not photos of Janice, not a real third party). Build the avatar **as-is** on this persona face, combined with Janice's real measurements and full-body proportions reference.

**Implications:**
- The Phase 2 exit gate changes from "feels like me" to **"matches the persona consistently + my real proportions."**
- Auto-QA identity scoring is against the persona face refs, exactly as the pipeline already works — no mechanical change.
- Renders are *styling visualization on a persona with my body*, not "how clothes look on my face." Fit/proportion signal is still real; face is fictional.
- If Janice later wants a true-likeness avatar, that's a new lineage (`avatar-v2`) from real unfiltered selfies — per plan §5.4, old renders keep their version tag.

## 2026-07-11 — Clean-skin avatar

**Decision (user):** Exclude the tattoos/markings visible in the real full-body photo. Every avatar and try-on prompt specifies clean, unmarked skin. `distinctive_features` stays empty by design.

## Reference photo inventory

| File | Role | Notes |
|---|---|---|
| `front face.png` (1536×1024) | persona face, front | AI-generated, warm indoor lighting |
| `left face.jpeg` (766×1024) | persona face, 3/4 | below 1024px spec — acceptable |
| `right face.jpeg` (778×1024) | persona face, 3/4 | below 1024px spec — acceptable |
| `full-body-upright.jpeg` (4284×5712) | body proportions only | real photo, rotated from `full-body.jpeg`; face/tattoos in it are NOT avatar canon |

**Prompt consequence:** face refs and body ref are different people, so avatar prompts must bind face to Images 1–3 and take only proportions from Image 4 (see `prompts/v1/avatar.md`). Skin tone follows measurements.json ("pale"), not the warm-lit persona photos.
