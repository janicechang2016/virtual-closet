# Virtual Closet (wardrobe-v3)

Photorealistic virtual try-on with a persistent personal avatar. Single-user, local-first.
Working code in `virtual-closet/`; plan in `virtual-closet-execution-plan.md`; running
decisions in `virtual-closet/docs/decisions.md` (read it — it carries the standing rules).

## Current state (2026-07-20)

- **360 MOTION-CONTROL PILOT READY (07-22, restart handoff):** after reviewing the
  completed 8-detent spin system, Janice chose to preserve the existing
  ChatGPT-generated `avatar-v3` and test a privacy-safe motion-control workflow
  instead of filming or exposing her real face. **Do not resume the old
  Wan-2.1 FLF2V eight-segment plan** and do not add more Fal credit for this
  pilot: independent video segments cannot fix the inaccurate turn geometry
  and are prone to seam/speed/identity/fabric drift. Fal is a usable inference
  marketplace, but `fal-ai/wan-flf2v` was the wrong endpoint/architecture.
  - **Chosen platform:** Kling AI native web app, **Kling VIDEO 3.0 Motion
    Control, Standard mode**. Janice confirmed she subscribed to Kling Standard
    (660 monthly credits advertised; Standard Motion Control = 9 credits/sec).
    First pilot is 10 seconds = **90 credits**. Do not fund Runway or Fal for
    this test. Native Kling was selected over Runway because it is cheaper and
    exposes facial Element binding/multi-angle identity references directly.
  - **Pilot look:** `look-006`, titled **look 001** —
    `03-patterned-dress + 52-camper-flats`. Its bold dress pattern and clean
    front/back references make garment crawling, rear invention, and temporal
    drift easy to judge. Character image =
    `renders/spin/outfit_03+52/f00.jpg`; appearance references = `f01..f07.jpg`.
  - **Privacy-safe driver built locally ($0):**
    `pilots/spin-motion-control/mannequin-turn-360.mp4` — procedural,
    appearance-free human mannequin, locked camera, exact constant-speed 360,
    720×960, 30 fps, 300 frames / 10 sec, no personal imagery. Rebuild with
    `scripts/motion_driver.py` using
    `/Users/janice.chang/liminal-wardrobe/.venv/bin/python`. This is a validation
    driver; Kling recommends real human footage, so the FIRST result must prove
    it understands the stylized mannequin before any broader spend.
  - **Complete upload/prompt manifest:**
    `pilots/spin-motion-control/look-001.json` records files, exact prompt, and
    acceptance criteria. Required Kling settings: Motion Control 3.0;
    Standard; 720p; Character Orientation = **Video** (must follow the driver's
    changing facing direction); original sound off; fixed camera. Bind a facial
    Element made only from the synthetic avatar if Kling offers it — never use
    Janice's real face/reference photo. The visible identity and outfit come
    from avatar/look references; the mannequin supplies motion only.
  - **Acceptance gate before another generation:** same synthetic avatar and
    body proportions throughout; dress pattern/hem stable; rear matches f04;
    feet planted; fixed camera and constant rotation; clean final→first loop.
    Stop if the first run shows major identity, garment, anatomy, direction, or
    pose drift; do not spend through failures reflexively.
  - **Browser handoff:** the stale desktop-AppTranslocation `node_repl` config
    had previously been removed. For the authenticated Kling workflow it was
    restored in `~/.codex/config.toml`, now pointing to the valid CLI plugin
    runtime at
    `~/.codex/plugins/cache/openai-bundled/chrome/26.519.81530/app-server-runtime/`
    (`node_repl` + `node`) and `CODEX_CLI_PATH=~/.local/bin/codex`. `codex mcp
    list` verifies `node_repl` enabled and no AppTranslocation path remains.
    **NEXT:** after restarting Codex CLI, Janice says “ready”; open her
    authenticated Kling session, upload driver + character reference, configure
    the settings above, then pause immediately before Generate to show the
    90-credit charge and get action-time confirmation. Generation is the first
  paid/external side effect. Download and QA the result before deciding on a
  second run or Luma/continuous-video comparison.
  - **FIRST KLING ATTEMPT REJECTED + FULLY REFUNDED (07-22 17:53):** Kling accepted
    the H.264 compatibility upload and quoted 90 credits, but its preflight after
    Generate returned **“No valid characters detected in the video.”** The UI
    explicitly says consumed credits were refunded (balance returned to 751), so
    no paid generation occurred. Root cause is the procedural mannequin being too
    abstract for Kling's human detector, not codec/duration/settings: the original
    FMP4 preview was black, then a locally transcoded H.264 copy previewed correctly
    before submission. **Do not retry the same driver or spend again reflexively.**
    Next requires choosing a more human-detectable but still privacy-safe motion
    source; keep the existing synthetic avatar as the character image and never
    upload Janice's real face.
  - **PHOTOREAL SYNTHETIC DRIVER BUILT ($0, 07-22 18:02):** Janice chose the
    privacy-safe retry. `scripts/avatar_motion_driver.py` turns the eight aligned
    synthetic look-001 avatar detents into a closed 300-frame sequence with local
    RIFE, then writes browser-compatible H.264. Output:
    `pilots/spin-motion-control/avatar-turn-360-h264.mp4` (10 sec, 30 fps,
    1024×1024, 1.4 MB). Contact-sheet QA shows a complete front→profiles→back→front
    human turn; no real-person imagery is present. `look-001.json` now points to
    this driver. **NEXT:** replace the rejected mannequin video in Kling with this
    file and verify it previews; keep Video orientation / Video 3.0 / Standard /
    720p. Confirm the quote is still 90 credits, then get approval before the one
    retry because this is a second paid attempt even though the first was refunded.
  - **KLING SYNTHETIC-DRIVER RESULT REJECTED (07-22 ~18:12, 90 credits):** result
    downloaded as
    `/Users/janice.chang/Downloads/kling_20260723_Motion_Control_A_fixed_ca_1568_0.mp4`
    (10 sec, 300 frames, 960×960). Janice: “entire figure morphs quite badly,
    it's scary.” Dense timeline QA agrees: the eight anchor orientations are
    recognizable in isolation, but the transitions reshape body volume, limbs,
    face and dress instead of producing a physical continuous rotation; facing
    also jumps/holds rather than maintaining constant angular speed. Root cause:
    Motion Control transfers the RIFE-generated synthetic morphs literally—it
    needs genuine continuous human motion, and neither an abstract procedural
    mannequin nor interpolated still-angle avatars supply that. **Hard stop on
    Kling Motion Control for privacy-safe synthetic drivers; do not spend on a
    prompt-only retry.** The result fails identity, anatomy, garment-stability,
    motion and loop acceptance gates. Keep aligned 8-detent scrub as the clean
    default unless Janice explicitly chooses a different continuous-video method
    or real human driver later.
  - **REAL-MOTION / PRIVATE-FACE DRIVER READY ($0 local, 07-22 19:29):** Janice
    recorded `/Users/janice.chang/Desktop/IMG_8576.MOV` (13.08 sec, 4K portrait,
    25 fps), a clean continuous full-body 360 in fitted black activewear. Original
    remains untouched and MUST NOT be uploaded: it contains her real face.
    `scripts/human_motion_driver.py` trims the clean 2.00–12.00 sec window to
    exactly 10 sec, downsizes to 720×1280, writes H.264, and covers her complete
    face/head envelope with an opaque tracked neutral oval. QA across 16 angles
    confirms no face leakage and clean front→back→front footwork. Upload-safe copy:
    `pilots/spin-motion-control/human-turn-360-private-h264.mp4`; manifest points
    to it. **NEXT:** upload this derivative only, bind facial Element from the
    synthetic avatar if possible, tell the prompt the gray privacy mask + black
    activewear are motion-only, verify Video orientation / 720p / 90 credits, and
    pause before a third paid attempt. Do not upload the original MOV.
  - **REAL-MOTION KLING RESULT: MOTION PASS, GARMENT-TRUTH FAIL (07-22 19:45,
    90 credits):** downloaded result
    `/Users/janice.chang/Downloads/kling_20260723_Motion_Control_A_fixed_ca_1943_0.mp4`
    (10 sec, 300 frames, 960×960). Full-timeline QA: the human driver fixes the
    scary synthetic morphing—identity/anatomy remain coherent, camera is fixed,
    the rotation is continuous, and frame 299 returns closely to frame 0. But it
    still fails the wardrobe-grade acceptance gate: the dress pattern crawls and
    is materially reinvented around the body; the generated rear is mostly
    red/black and does NOT match the strongly blue-backed f04 reference; real
    pivot-step footwork means feet are not planted. Keep as proof that genuine
    human motion solves geometry, but do not promote it as a faithful look-001
    360 or spend on prompt-only rerolls. Any next attempt would need an
    architecture with explicit multi-angle/keyframe garment conditioning during
    video generation, not Motion Control's single character-image appearance
    constraint.
  - **3D FOUNDATION PIVOT / AVATAR-V4 STARTED (07-22 ~20:05):** Janice explicitly
    approved scrapping avatar-v3 as the *foundation* if warranted. Decision: keep
    v3 as the published 2D visual/history, but do NOT reverse-engineer its
    inconsistent angle renders. Build a new canonical `avatar-v4` as a real 3D
    asset with stable topology, rig, proportions and garments. Installed Blender
    4.5.12 LTS user-locally at `~/Applications/Blender-4.5.app` (the Homebrew 5.2
    build crashes in headless Metal detection on this Mac); Blender commands need
    unsandboxed Metal access. Installed current MPFB from the official
    makehumancommunity/mpfb2 repo; local source/package are gitignored.
    `scripts/avatar_v4_blender.py` now deterministically builds a parametric Asian
    female MPFB body, game-engine rig, 300-frame linear 360 root animation, studio
    camera/lights, editable `.blend`, animated `.glb`, and front/rear gates under
    `avatar/avatar-v4/`. **V3-MATCH FOUNDATION PASS (07-22 ~20:32):** official CC0
    MakeHuman system assets now supply fitted low-poly eyes, young Asian female
    skin, long hair and sportswear. The hair is near-black and vertex-shaped into
    a restrained wave; the outfit shader reads as gray top + black leggings; face
    targets and a relaxed arm pose move the silhouette toward v3. Front/rear QA
    renders are clean, and the editable `.blend` plus animated `.glb` were rebuilt.
    Rejected experiments (torn automatic sleeve removal and floating curve bangs)
    were removed. This is now a usable 3D *foundation*, but not a finished likeness:
    **REFINED FOUNDATION PASS (07-22 ~20:43):** replaced the stock short-sleeve top
    with `punkduck_high_neck_crop_top` (clean fitted sleeveless silhouette), restricted
    the old sportsuit body mask to leggings only, and replaced the straight system hair
    with the longer black `elvs_lady_hippy_hair`. Added fitted eyebrows and eyelashes;
    rebuilt clean front/rear previews, `.blend`, and animated `.glb`. The two new assets
    are CC BY and are documented in `avatar/avatar-v4/ATTRIBUTION.md`. This is a much
    closer v3 art-direction foundation and the geometry is clean. Remaining mismatch is
    chiefly identity-level facial likeness and exact wispy-bang hairstyle, which now
    require manual sculpt/hair art rather than more library swapping. Do not wire it
    into the app as a v3 replacement until Janice approves the visible result.
    **FRINGE + LOOP PASS (07-22 ~20:57):** extracted only the fitted forehead fringe
    geometry from `elvs_katherine_hair`, layered it over the accepted long hair, and
    tightened the oval head/chin/eye/lip targets toward v3. The fringe is stable and
    clean at all angles. Rendered `avatar-v4-turntable-preview.mp4`: exactly 300 frames,
    30 fps, 10.0 seconds. Eight-angle contact QA confirms a constant-speed, fixed-camera
    360 with no morphing, geometry holes, clothing penetration, or angle-dependent
    identity changes. This is now the first usable game-selection-style spin proof.
    **V3-POSE MATCH + REVIEW ROUTE (07-22 ~23:36):** v4 now copies the canonical
    `avatar-v3/front.png` pose instead of inventing a generic mannequin stance:
    symmetric upright torso, vertical arms beside the thighs, palms facing inward,
    fingers down with a light resting curl, parallel legs, and v3's small foot gap.
    The rejected game-engine arm rig was replaced with MPFB's generated Rigify
    foundation. Arms and legs are explicitly switched to FK: shoulders lower the
    fitted A-pose, elbows extend through forearm controls, wrists remain neutral,
    and palms inherit a natural thigh-facing orientation without wrist roll.
    A spacing refinement reduced shoulder lowering from 40° to 37° to separate
    the hands from the thighs, and leg adduction from 8° to 6° for a natural
    foot gap. Rebuilt `.blend`, `.glb`, four-view previews, and the full
    A final hand refinement applies Rigify's `finger_curve=0.12` to the four
    finger master controls on each hand, subtly reducing side-view spread without
    moving the palms, thumbs, wrists, or arms. `avatar-v4-turntable-rigify-v3.mp4`
    is the current QA candidate. Eight-angle QA passes. Added isolated
    `/avatar-v4` comparison/review page (v4 video vs v3 canon; v3 remains production).
    Restarted the stale local server on port 8765 and verified both page and video
    return HTTP 200.
    **APPROVED V4 CHECKPOINT; RUNTIME EXPORT REJECTED (07-23 ~00:35):** Janice approved
    the final pose and finger spacing. Freeze that source at
    `avatar/avatar-v4/avatar-v4-approved-rigify-20260723.blend` with its companion
    `avatar-v4-approved-rigify-20260723-source.glb`; do not silently overwrite the
    checkpoint. The first reduced-skin GLB passed structural checks but failed
    visual QA catastrophically: stripping Rigify controls invalidated the skin
    bind and exploded the pose. Baking evaluated meshes fixed geometry, but the
    layered MPFB hair shaders still translated incorrectly to glTF (wrong blonde
    texture, then opaque hair cards masking the face). Janice rejected the result.
    **Do not expose or integrate `avatar-v4-runtime.glb`.** `/avatar-v4-runtime`
    now shows the approved turntable and a withdrawal notice; runtime/download
    links were removed from `/avatar-v4`. The approved `.blend` is unchanged.
    A future runtime asset needs a dedicated export rig plus baked PBR hair
    textures and must pass imported-GLB visual QA before browser use.
    **BAKED SPIN FOUNDATION RECOVERED (07-23 ~10:45):** the presentation-only
    runtime was rebuilt from evaluated frame-1 meshes, with no reduced Rigify
    skin. A clean parent root carries the 300-frame linear turntable. Export-native
    Principled materials use one color/alpha texture; skin and eyes are forced
    opaque because MakeHuman's legacy skin alpha incorrectly removes the face in
    glTF, while hair/brows/lashes retain alpha. Hair tint is baked dark and PNG is
    retained for lossless transparency. The resulting 6.2 MB Draco GLB passes
    import-and-render front/side QA: intact face, dark transparent hair, correct
    approved pose and clothing. `/avatar-v4-runtime` is restored and explicitly
    labels this as a stable spin/presentation foundation—not a photoreal final or
    garment-deformation rig. The editable approved Rigify checkpoint remains the
    source for the later dedicated game rig and photoreal material phase.
    **HAIR ART DIRECTION DEFERRED INTENTIONALLY (07-23 ~10:58):** Janice wants
    the finished hair to end at the upper-bust/top-of-breast line and the bangs
    to be straight across and wispy, not diagonally swept. Two nondestructive
    candidates proved the current library mesh cannot deliver that cleanly:
    vertical compression bunched the hair at the shoulders; a geometric trim
    produced a blunt card edge; procedural curve bangs read as wires. Both were
    rejected, and the review previews plus `avatar-v4-foundation.{blend,glb}`
    were restored from the immutable approved checkpoint. The validated runtime
    GLB was never rebuilt from either rejected candidate. Treat the requested
    silhouette as a requirement for the dedicated photoreal hair-modeling phase:
    use a purpose-built upper-bust hairstyle with proper alpha cards or groom
    curves, then retest front/profile/rear and browser transparency.
    **CUSTOM-GROOM PROTOTYPE REJECTED (07-23 ~11:28):** a dense tapered
    181-strand fringe was built and calibrated from floating in profile to seated
    against the forehead. It proved the head-plane placement, but still read as
    parallel lines rather than natural clumped wisps in the front view. Its
    promising upper-bust base (`culturalibre_hair_01`) was then found to be
    AGPL-3 in its `.mhclo`, which is unsuitable for the intended distributable
    app asset. Do not promote or ship it. The approved checkpoint, foundation
    aliases and four previews were restored; runtime was never rebuilt. The next
    hair candidate must be wholly original or clearly CC0/CC-BY, and should use
    clumped ribbon/card groups or a true groom rather than uniform parallel tubes.
    **ORIGINAL CARD-GROOM AUTOMATION REJECTED (07-23 ~11:33):**
    `scripts/avatar_v4_original_hair_candidate.py` built a license-clean scalp
    cap, 42 cross-card clumps and 17 tapered bang cards on a separate copy of the
    approved checkpoint. Four-angle output is saved as
    `hair-candidate-{front,right,rear,left}.png`; the editable rejected experiment
    is `avatar-v4-original-hair-candidate.blend`. Front QA fails decisively: the
    procedural cap reads as a helmet and the opaque grouped ribbons as flat strips
    across the face. Do not integrate or expose it. This confirms the required
    hair needs manual groom/card art (or a vetted permissively licensed production
    asset), not further procedural layout tuning. Approved previews, foundation,
    checkpoint and runtime remain untouched.
    **PHOTOREAL MATERIAL STUDY READY (07-23 ~11:48):**
    `scripts/avatar_v4_photoreal_material_candidate.py` opens the immutable
    approved checkpoint and creates a separate material/lighting study without
    changing geometry: restrained skin subsurface/specular response, moist-eye
    coat, matte brows/lashes, differentiated tank/legging roughness, and softer
    warm-key/cool-rim lighting. Outputs are
    `photoreal-candidate-{front,right,rear,left,face}.png`; editable study is
    `avatar-v4-photoreal-material-candidate.blend`; comparison route is
    `/avatar-v4-material-candidate`. Full-body QA shows a useful incremental
    material improvement, but the close face gate confirms current facial
    geometry and eye-obscuring hair are now the dominant realism constraints.
    Do not promote this as final photorealism or replace the approved checkpoint.
    **FACE MORPH GATE CONFIRMS MANUAL SCULPT REQUIREMENT (07-23 ~12:10):**
    `scripts/avatar_v4_face_geometry_diagnostic.py` renders the approved control
    plus balanced, soft-oval and tapered variants using only reversible MPFB
    shape keys. Both long hair and the fitted fringe are hidden for these frames
    so the eyes and facial silhouette can be judged. The comparison route is
    `/avatar-v4-face-diagnostic`. The variants produce only small proportional
    changes and cannot supply v3-level identity or photoreal facial anatomy.
    None is promoted or saved into the approved source. The next identity pass
    requires a manual sculpt/texture workflow; stock macro sliders are exhausted.
    **FACE REFERENCE SOURCE (07-23):** Janice tested ChatGPT and Gemini for the
    controlled v3 turnaround. ChatGPT outputs were rejected as visually strange
    and too identity/geometry-inconsistent. Use Gemini only for this pass.
    Highest-resolution source downloads belong in
    `avatar/avatar-v4/references/face/gemini/`; its README defines filenames.
    Treat them as sculpting references, never as replacements for v3 canon or
    the immutable approved v4 checkpoint.
    **PAUSED AT CLEAN FACE-SCULPT HANDOFF (07-23 ~16:40):** Janice explicitly
    approved `references/face/gemini/v3-face-front.png` as the locked facial
    identity master. The second Gemini pass is better but not perfectly
    self-consistent. Authority order is fixed: front controls identity,
    proportions and feature placement; `right-threequarter.png` is secondary
    transitional-volume guidance; `left-profile.png` is secondary depth guidance
    and should be mirrored for the opposite side. `left-threequarter.png` and
    `right-profile.png` are advisory only (identity/angle drift). Ignore all
    generated moles, pores, skin marks and cross-view asymmetry. Do not regenerate
    detail images: exact lossless crops are now
    `v3-face-eyes-crop.png` and `v3-face-nose-mouth-crop.png`.

    Nondestructive sculpt setup is complete:
    `scripts/avatar_v4_face_sculpt_setup.py` was run against
    `avatar-v4-photoreal-material-candidate.blend` and saved the separate
    **`avatar-v4-face-sculpt-workspace.blend`**. It contains locked, non-rendering
    front/three-quarter/profile image guides in collection
    `V3_FACE_SCULPT_REFERENCES` and a dedicated body shape key
    `v3-identity-manual-sculpt` initialized to the current approved face at 1.0.
    The immutable approved Rigify checkpoint, approved runtime, production site,
    and existing material candidate remain unchanged. Reference policy and
    filenames are recorded in `references/face/gemini/README.md`.

    Resume sequence (estimated 45–60 minutes for first pass):
    1. Open `avatar-v4-face-sculpt-workspace.blend`; work only on
       `v3-identity-manual-sculpt`.
    2. Keep both hair objects hidden for geometry QA.
    3. Make a conservative symmetric macro pass: match front face width/length,
       eye line and spacing, nose width, mouth width, jaw taper and chin; use the
       accepted left profile only for forehead/nose/lip/chin/skull depth.
    4. Do not chase pores, likeness texture, hairstyle, or generated asymmetry.
    5. Save a new candidate copy—never overwrite the workspace or approved
       checkpoint—and render front, right three-quarter, and left profile
       hair-hidden comparisons against the locked references.
    6. Expose results for Janice review only after visual QA; do not promote.

    `app/avatar-v4-face-references.html` and server route
    `/avatar-v4-face-references` were added as a local reference board, but the
    local server was intentionally stopped for this pause before it was restarted
    or the new route was HTTP-verified/opened. On resume, start
    `python3 scripts/closet_server.py` from `virtual-closet`, verify the route,
    then open it if useful. No commands or renders are running at pause.
    V3 remains the production fitting-room avatar: integrating v4 into garment
    fitting is the next product phase, not part of this approval checkpoint.
    **MANUAL SCULPT FIRST PASS (07-23 later):**
    `scripts/avatar_v4_face_sculpt_candidate.py` now builds a deterministic,
    separate first-pass candidate from the untouched sculpt workspace. Janice
    flagged candidate 02's left profile as monkey-like. Candidate 03 exposed an
    axis-sign error and is rejected; candidate 04 rebuilds from the workspace
    using the correct +Y facial plane, advances the nose relative to the lips,
    retracts the mouth zone, and balances the chin/forehead. Review files are
    `face-sculpt-candidate-04-{front,right-threequarter,left-profile}.png` and
    `avatar-v4-face-sculpt-candidate-04.blend`. It is cleaner but remains a
    review candidate only; do not promote or integrate without Janice's approval.
    Janice approved the direction ("this is better") and asked to continue.
    Candidate 05 relaxes the overly narrow head/chin/nose macro values, softens
    the V-shaped jaw, slightly lengthens the lower face, and broadens the
    eye/mouth proportions while preserving candidate 04's improved profile.
    Review files are
    `face-sculpt-candidate-05-{front,right-threequarter,left-profile}.png` and
    `avatar-v4-face-sculpt-candidate-05.blend`. Remaining mismatch is centered
    on the eye region; the source exposes scale/height/epicanthus controls but
    no safe eye-spacing control, so moving sockets would also require coordinated
    eyeball, lash, and brow edits. Candidate 05 is not promoted yet.
    **COORDINATED EYE PASS (07-23 later):** candidate 06 performs that coordinated
    edit nondestructively: both socket regions and the paired eyeball, eyebrow,
    and eyelash mesh halves move outward by the same ~3 mm per side. Front QA
    reads less close-set; three-quarter QA shows no floating/separation; the
    accepted candidate-04/05 profile relationship is unchanged. Review files:
    `face-sculpt-candidate-06-{front,right-threequarter,left-profile}.png` and
    `avatar-v4-face-sculpt-candidate-06.blend`. Still review-only; approved
    checkpoint, sculpt workspace, runtime, and production remain untouched.
    **READABLE QA + MIDFACE PASS (07-24):** candidate 07 preserves candidate 06
    geometry but reduces the overpowered studio lights and uses -0.55 exposure,
    revealing the nose, eyelids, mouth and jaw planes that the former whiteout
    obscured. That gate showed the remaining clear geometry issue was an overly
    pinched/low-volume nose. Candidate 08 relaxes the nose horizontal/volume
    reduction and slightly broadens the mouth while retaining the coordinated
    eye spacing and accepted profile. Front and three-quarter QA are more natural;
    left profile does not regress. Review files are
    `face-sculpt-candidate-08-{front,right-threequarter,left-profile}.png` and
    `avatar-v4-face-sculpt-candidate-08.blend`. Candidate-only; nothing promoted.
    **FACE/HAIR INTEGRATION GATE (07-24):**
    `scripts/avatar_v4_face_integration_preview.py` restores the current long
    hair + fitted fringe on candidate 08 and renders three angles into
    `face-sculpt-candidate-08-hair-*.png`; editable preview is
    `avatar-v4-face-sculpt-candidate-08-hair-preview.blend`. The face itself
    survives, but the hairstyle decisively fails: it covers one eye entirely,
    dominates the three-quarter view, and still reads too long/heavy. Do not
    adjust the accepted face around this rejected hair.
    License-first sourcing is recorded in
    `references/hair-license-shortlist.md`. The only plausible current import
    test is Greedy Engine's original **Wolf Hair** (Sketchfab listing: CC BY,
    57.3k tris); inspect the downloaded archive's embedded license and texture
    provenance before fitting. Explicitly reject the many Zepeto-derived
    Sketchfab uploads even when their listing says CC BY—the uploader credits
    Zepeto and does not establish authorship.
    **CURRENT-HAIR REPAIR REJECTED (07-24):**
    `scripts/avatar_v4_hair_layer_diagnostic.py` proves both layers fail on
    their own: the long base sweeps across an eye and the extracted fringe is
    an opaque asymmetrical cap. `scripts/avatar_v4_hair_open_face_candidate.py`
    then removed the fringe and symmetrically eased the licensed long-hair
    curtain away from both eyes. It exposes the face but tears/reveals the
    side-swept topology at the forehead (`hair-open-face-candidate-front.png`);
    reject it and do not promote. The current mesh is not repairable into the
    requested straight-wispy-bang silhouette. Replacement is mandatory.
    Authenticated Sketchfab download automation was attempted for the shortlisted
    Wolf Hair archive, but the Chrome connector failed twice at bootstrap with
    missing sandbox metadata before any page interaction. Janice must download
    the archive manually; once present locally, inspect embedded license/textures
    before importing into a separate candidate.
    **WOLF HAIR FULL FIT REJECTED (07-24):** Janice downloaded
    `wolf-hair.zip`; untouched archive, source, active texture and attribution
    are preserved under `references/hair/wolf-hair/`. Structural inspection:
    three meshes, one active included `HairStrand.jpg`, no linked libraries or
    executable content; listing is CC BY but archive has no license file.
    `scripts/avatar_v4_wolf_hair_fit_candidate.py` tested source orientation,
    180° orientation, crown-relative width/depth/length scaling, and exact
    face-plane alignment on candidate 08. Once correctly aligned, the asset is
    intrinsically an anime/card-shell cut: very tall scalp, heavy facial cards,
    fragmented alpha edges. Reject; do not integrate. Next license-clean
    candidate is miccall's **Female hairs** CC-BY eight-style collection,
    recorded in `references/hair-license-shortlist.md`; Janice must download it
    for archive inspection because authenticated download automation remains
    unavailable.
    **FEMALE HAIRS STYLE 02 FULL FIT REJECTED (07-24):** archive/source/eight
    textures/attribution preserved under `references/hair/female-hairs/`.
    Inspection passes structurally (eight meshes, packed numbered textures, no
    linked libraries; only unused HDR missing). Standardized source thumbnails
    live in `references/hair/female-hairs-inspection/`; style 02 was the closest
    straight-bang upper-bust silhouette. The full candidate fit is
    `avatar-v4-female-hair-02-fit-candidate.blend` with four
    `female-hair-02-fit-candidate-*.png` gates. It fails intrinsically: `02.png`
    has no alpha, so broad beige scalp/face cards render over the skin; deleting
    central below-brow cards reveals coarse jagged ribbon topology and scalp
    holes. Dark strand-preserving tint cannot fix geometry. Do not integrate.
    Two separate CC-BY free-asset families have now failed full import/fitting;
    next credible path is a vetted production hair-card asset or genuinely
    manual groom, not more automated deformation of low-quality free meshes.
    **PAUSE / LATEST HANDOFF (07-24):** Janice asked to save state and is
    considering returning to the 2D product and trying a different approach.
    Do not continue face/hair/3D work automatically. Face candidate 08 remains
    the best isolated facial candidate; no v4 source, runtime, hair candidate,
    or route has been promoted into the production fitting room. The latest
    style-02 hair render is rejected, not a checkpoint.

- **2D ROLLBACK / 360 ISOLATION MAP (07-24):** yes, the spin work can be isolated
  without deleting it. Committed spin history lives on `main` from the first
  spin commit `c9b8310` through `f867251`; the literal pre-spin merge boundary
  is `a71062d` / tag `fitting-room-pre-360`. The preferred 2D product baseline
  is the separately reconstructed commit/tag **`fitting-room-pre-360-ui-final`
  (`8c7532f`)**, already pointed to by local/remote `production`; it includes
  the later desired index/silver-hover/reorder/18-look/demo-chrome changes and
  contains no spin code or assets. Important: `8c7532f` is a sibling lineage
  whose merge-base with `main` is `a71062d`, not an ancestor to reset through.
  Safest future operation:
  1. preserve current dirty v4/pilot work on a dedicated archival branch/commit;
  2. leave `main` and its pushed spin commits untouched as the 360 archive;
  3. create a fresh `2d-reboot` branch directly from `8c7532f`;
  4. selectively bring over only explicitly wanted non-spin research/assets.
  Do not run a hard reset or bulk checkout in the current dirty worktree.

- **THE LOOKS ERA (07-19–20):** she published 19 looks (~$1.19) and then deleted one,
  so the archive is **18 published looks**, titled **"look 001"–"look 018"**. Title ≠ id
  and the drift is now large — carousel order is her 07-20 drag pass: **look-006 leads**,
  then look-014, look-013, … look-023 last (read `looks.json` for the live mapping;
  don't assume title order matches id order). `look-015` (43+44 subtle-mermaid set +
  52 flats) **deleted by her via the UI 07-20** — renders stay on disk
  (`outfit_43+44+52_1*.png`) and the entry survives in commit `8b309cc`, so restoring
  is $0. Server default-titles new looks from the *id* number, so the next save
  suggests "look 024" — rename at the prompt.

- **ORDER IS THE `looks.json` ARRAY (07-20):** nothing sorts anywhere — `load_looks`
  preserves file order, `buildItems` walks it — so reordering is a **$0 edit, no
  re-renders**. **`START_LOOK` is now `null`** = land on whatever is FIRST; it had been
  pinned to `look-006`, which silently swallowed a manual reorder and made it look
  like reordering "didn't work". Set it to a look id only if you want a fixed hero
  again — and know that it hides order changes when you do.
  - **DRAG-TO-REORDER SHIPPED 07-20** — index lens only (the grid is the one place
    order is legible; the carousel stays read-only). Pointer-driven cell drag w/
    floating ghost card, dimmed source, 3px black insertion bar; 6px threshold keeps
    a plain click opening the detail overlay (a committed drag rebuilds the grid so no
    trailing click fires; an aborted one is swallowed by a one-shot capture listener);
    ESC aborts. Optimistic → `POST /api/looks/reorder {order:[ids], renumber:true}`,
    reverts + alerts on failure. Server permutes only the payload's ids among the slots
    they already own, so drafts hold absolute positions. CDP 13/13
    (drag mechanics, persistence, renumbering, click-vs-drag, hero-follows-order).
  - **Titles follow position, on BOTH write paths (07-20):** shared `renumber_looks()`
    — the nth *published* look is "look 00n"; custom names survive but still consume
    their slot number; drafts untouched. Delete used to skip renumbering and leave a
    hole (that's how look-015's gap at "look 012" appeared) which the next drag would
    then silently close; the two paths now agree by construction. `/api/looks/delete`
    returns the refreshed `looks`, and the fitting room already re-fetches the manifest.

- **DEMO CHROME PARED BACK (07-20, static export only):** `body.demo` now also hides the
  **budget meter** (`#nav-cost` + `#cost-meter`, plus its dangling separator dot in the
  fitting-room strip) and the carousel's **"Archive demo" status line** (`#nav-gen`) —
  nothing is spendable from the export, so a frozen $/cap is just a question generator,
  and the public build shouldn't announce itself as a demo. The deployed carousel's
  top-right now carries only the avatar version. **Local is unchanged** (meter live,
  line reads "Generation live"/"Copy-prompt"). The fitting room still shows
  "read-only demo" in its strip — left deliberately, rewording is an open offer.
  **Why the deploy is read-only at all:** it's a static snapshot with no Python process
  and no `FAL_KEY`, so renders/publish/save/delete/reorder/sourcing/spin are all
  server-dependent and gated off; browsing, index lens, detail overlay and
  drag-to-dress swaps work fully. Hosting it truly live would put a public endpoint in
  front of the fal budget — **declined 07-20** as against the standing $0-first rule.

- Carousel = **outfits only** (see the two-views section). A vortex-boots look was
  deleted by her via the UI 07-19 (renders stayed on disk), as was look-015 on 07-20.
  **`look-023`** (59-el-hoodie + 42-sagittarius + 56-mizuno — titled "look 018" as of
  the 07-20 renumber) went through the full gauntlet: zip-up invention corrected, pants
  length corrected (meta was wrong, not the render), **hood-up variant is its carousel
  figure** (Janice's pick; hood-down `_2` kept unhidden as chain reference).

- **360 SPIN FULL BATCH COMPLETE (07-22): every garment (58) and every published
  look (18) has all 7 angle frames, QA'd on contact sheets + full-size checks.**
  Janice's back-photo drop (24 files) ingested into per-garment raw/ (avif→png,
  woodrose 47/48 upgrades demoted old shots to `_back2`); retention tag
  **`pre-spin-full-batch`**, final state pushed at `9fc9e92`. Total spend
  $38.97/$45 (~$26.9 for the batch incl. ~35 corrective frames). Systemic fixes
  now live in `spin_frame` (decisions.md 07-22): base-outfit **keep anchor**
  (lone bottoms tripped nb2's checker as implied undress), **legwear/dress
  rulings** (bottoms replace leggings, dresses replace tank+leggings, unless a
  `wear_note` overrides — 47 keeps leggings per canon), **worn-alone wear_notes**
  on tops whose canon has no gray tank under (11/12/13/16/19/23/24), `back_note`
  rear-frame hints for garments with no back photo (43/44 Subtle Le Nguyen:
  plain-white mirrored backs per Janice — rendered exactly so). 36-liv meta
  color was a WRONG vision tag (corrected to black w/ red roses). `fal_generate`
  polls 15 min + logs request_id on timeout (the old ~4-min window silently
  abandoned billed jobs). **fal balance ran dry twice mid-batch** — genlog
  tracks HER cap, not fal's balance; her top-ups also take a few minutes to
  unlock the account (a status-endpoint 202 does NOT mean submits work).
  Invented rears (no back photo, flagged for her scrub-through): 01/02/05→no,
  08/09/10/15/18/27/29 + 43/44-by-note. Known leftovers for her judgment:
  26 drape wobble, 31 long corset laces, 48 bare-back-per-product-photo,
  look-010 a180 invented rear print.
- **SPIN VIEWER SMOOTHING (07-22, $0): aligned detents, NOT interpolation.**
  `scripts/spin_smooth.py` normalizes the 8 real frames onto one shared canvas —
  nb2 draws the figure 974–1755px tall on differing canvases (560×1835, 843×1264…),
  which was BOTH the "grey square / mirror changes size" complaint AND why naive
  RIFE interpolation ghosted. Fix: frame 0 = untouched canon (entering spin
  changes nothing on the mirror); frames 1–7 rescaled via rembg human-seg to the
  canon's figure height, feet on its baseline, centered on its axis/canvas, padded
  with each frame's own edge tone. Output `renders/spin/<key>/f00..f07.jpg`
  (gitignored, rebuild `spin_smooth.py --all`; key = garment id or outfit stem).
  `/api/spin` probe returns `norm` (8 aligned); viewer scrubs them with the
  crossfade (app.js `setSpinPos`), mirror stays rock-constant (CDP: 618×603 all
  frames). Posed-front looks (hand-on-hip/contrapposto/34turn — no neutral front
  render) fall back to the posed render as frame 0: mirror still constant, but the
  pose carries into the 0° detent (34turn reads as a slight pre-turn — flag for
  Janice). **RIFE interpolation PARKED** (`tools/rife-ncnn-vulkan`, gitignored;
  `spin_smooth.py --interp` still runs it): the turn-base quarters run shallow
  (~20°), so the a045→a090 gap is a ~70° rotation — optical flow smears the face
  mid-gap (Janice saw it "wrong ~frame 10 on"). True continuous rotation would
  need image-to-video segments (tier 3, below).
- **TIER-3 SPIN VIDEO (07-22, BUILT + wired; BLOCKED on fal balance):** for a few
  chosen HERO looks only (tier 3 costs real $; most items/looks stay on the $0
  tier-2 detent scrub). Architecture Janice chose: hero looks auto-play a slow
  360 loop when opened from the carousel. **All built, presence-gated, dormant
  until a `loop.mp4` exists:**
  - `scripts/spin_video.py` — feeds each adjacent pair of a look's 8 aligned
    detent frames (`renders/spin/<key>/`) to **Wan-2.1 FLF2V** (`fal-ai/wan-flf2v`,
    both endpoints are our QA'd frames so identity can't drift far), stitches the
    8 segments (cv2, no ffmpeg — dropping each seam's dup frame) into
    `renders/spin_video/<key>/loop.mp4`. Cost **$0.40/seg @720p = $3.20/look**
    ($1.60 @480p). `fal_generate.generate_flf2v()` carries the budget gate + genlog
    + 15-min poll; genlog `COST_TABLE` has `wan-flf2v: 0.40`.
  - Server `looks_list()` sets `spin_video` URL when the loop exists; carousel
    `openDetail` swaps in `#detail-video` (autoplay, loop, muted, playsinline,
    `playbackRate 0.5`) for those looks, still image otherwise. `.mp4` serves
    fine via the existing `/assets/` route (guess_type → video/mp4).
  - **STATUS:** 1 pilot segment (05 f00→f01, 720p, $0.40) generated but
    UNRECOVERED — fal `wan-flf2v` queue was badly congested (~40 min IN_QUEUE),
    then the account **locked on exhausted balance** before the result could be
    fetched. request_id `019f8b35-0d15-7f41-99fa-2556b24f03fd` — recover its
    result URL for $0 once unlocked (`generate_flf2v` logged it).
  - **BLOCKER = fal balance, not code.** Janice's fal balance sat at **-$0.08**
    (hovering at zero all day — the real cause of ALL the mid-batch locks; NOT
    shared with other projects, she confirmed). Plan: small top-up → recover the
    paid pilot seg → she judges motion quality → if good, $15-20 top-up + raise
    genlog cap (>$45, currently $38.97) + build her 2-3 chosen hero looks
    (candidates floated: look-023 hoodie set, look-014 sweater/skirt/boots, a
    dress like 017/022). Queue slowness means hero builds are background-and-wait.
- **360 SPIN (07-19, BUILT + pilot CLEAN; full batch HOLDING):** fitting-room ONLY —
  Janice amended her "poses/angles are archive-only" rule for angle frames; archive
  posed-look system untouched; correctives stay front-frame-only. 8 frames at 45°
  (`avatar/avatar-v3/turn-045…315.png` — Janice-supplied nano-banana singles off
  front.png, originals in `avatar/turn-bases-original/`, aligned via human-seg
  bboxes to front.png geometry; quarters run shallow ~20°, accepted). Pipeline:
  `tryon.py` ANGLES/`spin_frame` (rear frames auto-attach garment `*back*` raw
  photos as ground truth; face-swap ONLY on a045/a315 — no face on rear/profile
  frames, so those cost $0.039 not $0.059; `--spin` CLI), `/api/spin` (probe =
  frames/cost/no-back warnings; then per-angle generate so progress shows and
  aborts resume free), angle stems (`_a###_`) filtered like pose tags, mirror
  scrub viewer (drag 40px/frame, ESC exits), billed-batch confirm modal, and the
  **receive gesture baked in**: garment dragged over a mid-spin mirror steps her
  back to front first, then front-receive plays. CDP 11/11 with stubs. **Pilot
  (`look-023` hoodie combo, $0.31) CLEAN** — band continuity via back photos, profiles
  correctly handed (small contact sheets MISLEAD on handedness; verify full-size).
  **Cap raised to $45 (Janice +$20, credits confirmed). Full batch = 58 garments +
  18 outfits ≈ $23.79 — HOLDING until her back photos land** (else ~35 invented
  rears get paid twice). Back-photo priority list delivered 07-19 (A: distinct
  backs — 03/05/06/07/37/43/44, dresses; B: all shoes need heel views; C: symmetric
  basics skippable); 3 backs + 2 sides rescued from mislabeled `_alt` files ($0).
  Fitting-room spin of a look needs its front-pose outfit render first (~$0.059).
  Her server was restarted 07-20 and now carries `/api/spin` and
  `/api/looks/reorder` — but it came back up **without `ENABLE_GENERATION`**, so
  restart it with the env var before any billed run.

- **Index lens (07-19, SHIPPED):** `/?view=index` or the **Carousel / Index toggle**
  in carousel.html nav-left — dense SYVE hairline grid of all published looks over
  the carousel (native scroll; wheel/touch/morph guarded; #info/#controls hidden
  while up; cells open the shared detail overlay). Hover = **chrome-silver gradient
  wash** (Janice rejected the black invert as too heavy; the silver is a deliberate
  whisper of the shelved Holo Mirror skin). CARD-PIPELINE's transferable polish
  kept (one figure height, bottom baseline, min-height captions).

- **59-el-hoodie ingested + rendered (07-19):** Janice's "EL-hoodie" webps =
  **Eckhaus Latta** (baked-in shoulder print identified it), painted-band pullover,
  size M, difficulty 3, model front/alt/back views banked. Render `_1` invented a
  full-zip worn open → **new failure flavor: nb2 invents garment CONSTRUCTION** —
  root cause: BOTH prompt paths hard-coded outer layers "worn OPEN". Fix: per-garment
  **`wear_note` meta override** (59: "worn CLOSED as a pullover — no zipper") honored
  by single AND outfit paths; outfit path also finally carries `exclude_from_photo`
  (the 07-16 fix had only reached the single path). Also: 42-sagittarius meta said
  "cropped ankle" — WRONG vision tag, pants are full length (owner's word + product
  photo override auto-tags; meta corrected).

- **README (07-19):** outfits-only carousel copy; fitting-room visual is now an
  **animated drag-to-dress GIF** (`docs/screenshots/fitting-room-drag.gif`, CDP
  screencast capture at $0, ~5MB — per-frame palettes REQUIRED, shared palettes
  speckle the face red); sourcing screenshot added + note that the static demo
  excludes /sourcing (live-server dependent). Fresh 1440×900 captures of both views.

- **Fitting room looks rail (07-19):** looks index scrolls independently (slots +
  action buttons pinned, racks' 6px black scrollbar), per-row "in archive" badge
  dropped (publish button marks drafts), save scrolls the new draft into view.
  A look hover-preview frame was built, shown, and **REJECTED by Janice — do not
  rebuild.**

- **Repo on GitHub (07-17):** github.com/janicechang2016/virtual-closet — PRIVATE
  until Janice flips it for the portfolio; all rollback tags pushed. **README
  added 07-18** (repo root, first-person as Janice, portfolio-facing: two views,
  pipeline + $0.059/render, budget story, rights note re retailer product photos;
  UI screenshots in `virtual-closet/docs/screenshots/` — headless-Chrome captures,
  she may swap). **Static Vercel export ($0):** `python3
  scripts/export_static.py --out site` snapshots the manifest (`demo: true`,
  generation off) + copies referenced assets (~80MB, 303 files) into `site/`
  (gitignored); root `vercel.json` runs it as the build command with rewrites
  for `/`, `/fitting-room`, `/api/manifest`. The app UIs gate on `M.demo`
  (body.demo CSS): Sourcing link, feedback bar (visibility — footprint kept,
  mirror must not shift), SAVE LOOK / RENDER OUTFIT / publish / delete /
  carousel CTA all hidden; read-only browsing + drag-to-dress instant swaps
  fully work from static files. `M.demo` is never set locally — zero behavior
  change for the live server. Vercel import is Janice's (she owns deploys);
  suggest Deployment Protection until the repo goes public.
  **CORRECTED PRODUCTION BASELINE (07-23):** The literal pre-spin boundary
  `a71062d` is preserved as `fitting-room-pre-360`, but it predates independent
  later UI work Janice wants in production. The actual production baseline is
  annotated tag **`fitting-room-pre-360-ui-final`** at reconstructed commit
  `8c7532f`: `a71062d` plus only the later non-spin index lens, silver hover,
  drag-to-reorder, 18-look deletion/renumbering, hidden demo budget, and removed
  "Archive demo" line. It contains no 360 pipeline, viewer, scrub, API, or spin
  asset references. This tag is the easy production rollback target. Vercel
  production `virtual-closet-seven.vercel.app` was deployed from its isolated
  prebuilt export and verified: `/`, `/fitting-room`, and `/api/manifest` HTTP
  200; Index present; 18 published looks `look 001`–`look 018`; no spin strings.
  A dedicated remote **`production` branch** also points to `8c7532f`, and the
  Vercel project's Production Branch setting was changed from `main` to
  `production`. Therefore pushes to `main` may create previews but must not
  replace production. **Production contract:** keep
  `fitting-room-pre-360-ui-final` live in production; all 360-spin and v4 work
  stays local/on development branches until Janice explicitly approves a
  production release. Do not merge or cherry-pick spin/v4 commits into
  `production`, and do not reset or discard that later work locally.

- **Mirror reaction (07-17, $0):** while a dragged garment hovers the mirror and the
  stage shows the base avatar, it crossfades to `avatar/avatar-v3/front-receive.png`
  (Janice-supplied nano-banana edit of front.png; locally aligned via human-seg
  bboxes, original at `avatar/avatar-v3-front-receive.png`); drop holds the
  receiving frame ~220ms before the render lands. **UI frame only — never a render
  base.** Renders on stage get the CSS breath (scale 1.015 + brighten) instead —
  per-render hover variants deliberately rejected (cost + face risk). Drag ghost:
  50/57 items fly as bare transparent silhouettes (`scripts/dragcut.py`, run at
  every ingest; on-model→cloth-seg only NEVER general fallback [person-ghosts],
  product shots→general model), 7 fly as framed cards. CDP suite: 11 checks
  (`scratchpad dnd_test4.py` pattern — synthetic PointerEvents via
  --remote-allow-origins=*).

- **Catalog is now 58 active garments** (01–05 benchmark + 53 ingested 07-16 +
  59-el-hoodie 07-19; 22-gnur-hoodie ARCHIVED 07-16 by Janice — folder in
  `garments/archive/`, renders in `renders/archive/`, restore = move back;
  sizes/brands per `docs/ingest-worksheet.md`, Janice-filled; ingest
  details in decisions.md). raw/ naming: primary view = plain slug (sorts first for
  garment_asset), extras `_back/_side/_alt/_model-*/_detail`; avif→png at ingest;
  transparent sources composited on white (transparency reads as black downstream).
  Difficulty-4/5 (front-only): 23/24 issey, 26 liniss dune, 29 nin, 40 sheer top,
  43/44 subtle-mermaid (a SET, wearable separately, cross-noted). 22 gnur has a
  cloth-seg `_onwhite` (source was grey-on-black). **All 58 rendered + cutouts done
  (07-16, $3.25 + $0.53 fix round, spend $10.13/$25):** batch QA'd on contact sheets;
  10 failures traced to prompts missing the not-part notes → fixed via `SLOT_NOTES`
  category anchor + `exclude_from_photo` meta field in tryon.py (fill it at ingest
  for on-model photos!); 9 re-rendered clean (`_2` suffix, bad `_1`s hidden);
  30-off-shoulder borderline-kept; 45 sundae corrective 07-16 (pasted-on → worn,
  _1 hidden). **Drag-to-dress SHIPPED 07-16, ISC physics + bare silhouettes 07-17**
  (pointer-driven per kaberikram/Interactive-Styling-Canvas: garment cutout rides
  the cursor w/ grab lift + directional tilt + fly-back; 50/57 items fly as bare
  transparent silhouettes via `scripts/dragcut.py`, 7 as framed cards; mirror
  brightens on hover; base avatar swaps to `avatar/avatar-v3/front-receive.png`
  while a garment hovers the mirror + ~220ms "she takes it" hold on drop (UI frame
  ONLY — never a render base; Janice-supplied, locally aligned); drop = slot assignment + tryOn instant swap; position ≠
  meaning; CDP-verified; rollback tag `pre-drag-to-dress`). Collage preview = maybe-later. 360/turntable parked —
  revisit after renders; grab garment BACK views when sourcing.

- Phases 0–4 complete. **avatar-v3 is canon** (2026-07-14): user-supplied 4-pose library
  in `avatar/avatar-v3/` (front / contrapposto / hand-on-hip / 34turn) — new lineage
  superseding avatar-v1 (v1 4-view sheet kept in `avatar/avatar-v1/`). **Whole catalog
  re-rendered on v3 poses 07-14** (`tryon.py --pose <name>`, works for `--outfit` too;
  v1 renders legacy on disk, old look renders in hidden.json). Pose map: 01
  contrapposto, 02 hand-on-hip, 03 front (Janice rejected its drifted contrapposto —
  hidden via hidden.json, which now also governs cutout choice in the server AND
  cutout_render.py), 04 34turn, 05 front, look 01+02 34turn, look 01+02+04 hand-on-hip.
  One pose per saved look; difficulty-4/5 garments stay on front. **Poses are
  archive-only (Janice 07-14): the fitting room shows/corrects front renders exclusively**
  (server filters pose-tagged stems from `renders`). **AMENDED 07-19 for angle
  frames only:** the 360 spin's `_a###_` frames live in the FITTING ROOM (scrub
  viewer); posed looks remain archive-only and correctives remain front-only. Front v3 renders exist for all five
  garments (01–04 batch $0.235, approved 07-14; 02 corrected twice via the feedback
  loop — navy→pure black, then waistband removed → `02-jeans_nb2_v3_4.png`).
  **Lesson (07-14): chained correctives compound face drift** — two stacked nb2 edits
  made 02's face uncanny despite face-swaps (each edit re-synthesizes the head; swap
  restores identity, not skin texture). Batch fixes into ONE corrective note when
  possible; after edits degrade a face, transplant the head from the cleanest render
  of the same chain locally ($0, alignment is pixel-close) → `02-jeans_nb2_v3_5.png`.
  05's front render was frame-padded locally to square 1824² to match the 1024² v3
  renders (nb2 returned a 1:3 sliver; original at `renders/archive/*_prepad.png` —
  `renders/archive/` is app-invisible).
- Phase 3 benchmark done (`docs/phase3-benchmark.md`): default try-on pipeline is
  **fal-ai/nano-banana-2/edit + fal-ai/face-swap finish** ($0.059/render). NB Pro is worse
  at try-on (re-stages scenes); IDM-VTON needs its `category` param wired.
- Server `scripts/closet_server.py` → http://localhost:8765 (run with
  `ENABLE_GENERATION=1` for live spending). Single-item try-on, multi-item outfit compose,
  feedback→corrective-edit loop, clear-to-base, look save/publish/delete
  (`/api/looks`, `/api/looks/delete`, `/api/publish`) — all working from the UI.
- **`/sourcing` — photo-sourcing UI (07-15):** SYVE-styled third page over
  `ingest_fetch.py` (imported as a module; the only route needing `requests`).
  Paste a product URL → `/api/source/scan` ranks candidates (bytes held in
  memory, served via `/api/source/img?i=`; browser measures real dims —
  server python has no PIL), click-select → `/api/source/save {picks, slug}`
  writes `garments/raw/<slug>.<ext>`. Staged strip lists `garments/raw/*` with
  <1000px "thumb — re-source" flags (currently flags yello-heels, mizuno,
  asics, keen); × discards to `garments/raw/_discarded/` (move, not delete).
  Slug auto-derives from page `<title>`. CLEAR (ghost button, appears after a
  scan) resets the page + drops the server cache (`/api/source/clear`).
  `?url=` prefills + auto-scans (bookmarklet-friendly). Linked from both navs. $0, works without
  ENABLE_GENERATION.
- **One brand ("the archive."), two views, one SYVE language** (white void, black 1px
  hairlines, uppercase Helvetica, italic lowercase wordmark):
  - `/` — **SYVE-style carousel** (`app/carousel.html`, single-file): **OUTFITS ONLY
    as of 07-19** (queued item triggered by Janice with 19 looks published, 18 now — buildItems
    shows published looks exclusively, category filter nav removed, nav-left = Fitting
    room / Sourcing links; single garments stay in the fitting room racks). Figure
    cutouts (from `scripts/cutout_render.py`, rembg u2net_human_seg), spec-faithful slot
    interpolation + infinite wrap + 80px snap/dwell, x-axis scroll + click-to-center;
    hero slot at 85% of spec size (Janice: full size
    too big); snap ease slowed to 0.08 (07-14); hero click opens the detail overlay
    (item rows + pose, RE-RENDER LOOK wired to the publish pipeline, OPEN IN FITTING
    ROOM as the black primary). Spec: `virtual-closet/design-inspo/`
    (docx + reel).
    A **runway-procession variant** (single-file line receding to a vanishing point, per
    `design-inspo/runway-inspo.avif`) was built and shelved same night — saved at tag
    `runway-procession-v1` (restore: `git checkout runway-procession-v1 -- virtual-closet/app/carousel.html`).
    An **auto-scroll variant** (ambient drift + hover slow-to-crawl) was built and shelved
    2026-07-14 — saved at tag `auto-drift-v1` (restore:
    `git checkout auto-drift-v1 -- virtual-closet/app/carousel.html`).
    **ASCII entrance SHIPPED 07-15** (in carousel.html, from Janice's design handoff at
    `design-inspo/design_handoff_ascii_entrance/`, SYVE-skinned): full-bleed cleaned
    grayscale interior (`app/entrance-bg.jpg`), black glyphs of the handoff quote trace
    its edges (charSize 12, shimmerDepth 0.9 — new knob, handoff twinkle invisible in
    b/w), "enter the archive." label; click → pulse-fade dispel (glyphs stop reappearing,
    photo fades to white, NO ghost) revealing the live carousel; once per session
    (`sessionStorage.archiveEntered`), reduced-motion skip, `?entrance=1/0` debug.
    Previews kept in `design-inspo/entrance-previews/` (options 1–3; see decisions.md).
  - `/fitting-room` (`/classic` kept as alias) — **fitting room** (outfit rail | stage |
    racks). Design lineage: Boutique v3 (313NY, tag `boutique-v3`; amber rejected as
    masculine, violet/rose rejected outright) → SYVE restyle 07-13 (tag
    `fitting-room-syve-v1`) → **prettier pass 07-14** (current): mirror stage + gallery
    label, text-first index racks with hover preview, manifest outfit rail, "Nº 313"
    copy removed. Feedback bar keeps its footprint when hidden and fades in place
    (07-15) — appearing must never shift the centered mirror.
  - `renders/hidden.json` — render stems the server keeps out of the app (files stay on
    disk). Size row reads `size_owned` from each garment's `meta.json`; unset = no
    highlight (log real sizes at ingest — not everything is S).
- **Two-view architecture BUILT (2026-07-14, user-approved):** home = archive (`/`);
  fitting room at `/fitting-room` (`/classic` alias). The **look is the atom**:
  `looks.json` is the canonical store (draft → published lifecycle; see decisions.md).
  Doors: archive hero click → detail overlay (items+sizes, pose, re-render, OPEN IN
  FITTING ROOM → localStorage handoff into slots); fitting room SAVE LOOK = free draft,
  PUBLISH = pose-picker + $0.06 render + cutout → appears in carousel. Cross-document
  view transitions morph the hero ↔ stage (`view-transition-name: figure`) — polished
  07-14: 0.55s soft-ease morph over a 0.35s root crossfade; the detail overlay's image
  anchors the morph while open; plain header links clear the names (quiet crossfade,
  morphs reserved for the deliberate doors). Publishing runs the cutout pass via the
  liminal venv subprocess. Poses remain archive-only,
  no exceptions (Janice 07-14): looks arriving via OPEN IN FITTING ROOM load the slots
  and show the base avatar. **Prettier pass shipped 07-14** (mirror stage + gallery
  label, text-first index racks with hover preview, manifest outfit rail — see
  decisions.md); pre-pass design tagged **`fitting-room-syve-v1`**
  (revert: `git checkout fitting-room-syve-v1 -- virtual-closet/app/`). Garment `meta.json` has a `brand` field (all five
  filled — Peachy Den / In This Era / Nin Studio / Musinsa Standard / Woodrose Deli),
  shown as the first line of the archive detail overlay; fill at ingest for new items.
- Spend: **$12.09 of $45 cap** (`python3 scripts/genlog.py summary`; cap raised from
  $25 on 07-19, Janice +$20 for the spin batches). Big items: July catalog batch
  $3.25 + $0.53 fix round; Janice's 19-look publish run ~$1.19; hoodie saga $0.24;
  pilot spin $0.31. Reserved: ~$23.79 for the full spin batch (holding — one fewer
  outfit since look-015's deletion).

## Standing rules

1. **Spending:** fal calls only in user-approved batches/envelopes. All calls go through
   `scripts/genlog.py` budget gate; never bypass it.
2. **Identity:** every render with a visible avatar face gets a `fal-ai/face-swap`
   finishing pass, source `avatar/avatar-v3/front.png` (v3 canon 2026-07-14; v1 renders
   are legacy lineage). Never edit the avatar's head region with NB models (edits collage
   or regress the face — regenerate instead).
3. **Prompts for nb2/edit must be neutrally worded** ("virtual try-on: show the person
   wearing…", never "dress the woman", no body-size adjectives) — its content checker is
   strict. Anti-collage phrasing ("one single figure, not a collage…") in every prompt.
4. **Renders:** `renders/<garment>_<arm>_v3[_<pose>]_<n>.png` (v1 = legacy lineage);
   look renders `outfit_<nums>[_<pose>]_<n>.png`; `_raw` = pre-swap intermediate
   (excluded from the app). Garment-id prefix is how the app matches renders;
   `renders/hidden.json` hides stems from render lists AND cutout choice;
   `renders/archive/` is app-invisible.

## Key commands

```bash
ENABLE_GENERATION=1 python3 scripts/closet_server.py     # app (from virtual-closet/)
python3 scripts/tryon.py <garment-id>                    # one try-on render
python3 scripts/tryon.py <gid> --pose contrapposto       # render on an avatar-v3 pose base
python3 scripts/tryon.py --outfit 01-plain-tee 02-jeans  # multi-item compose
python3 scripts/tryon.py <gid> --correct "wrong fit" --note "…"  # corrective edit
python3 scripts/tryon.py <gid> --spin                    # 7 missing 45° spin frames (garment)
python3 scripts/tryon.py --outfit <gid> <gid> --spin     # spin frames for an outfit combo
python3 scripts/genlog.py summary                        # spend vs cap
/Users/janice.chang/liminal-wardrobe/.venv/bin/python scripts/extract_garment.py  # cloth-seg cutouts
/Users/janice.chang/liminal-wardrobe/.venv/bin/python scripts/ingest_fetch.py URL [SLUG]  # $0: pull best product image from an ecomm page into garments/raw/ (--list to rank, --pick N to choose, --keep N for extra views)
/Users/janice.chang/liminal-wardrobe/.venv/bin/python scripts/dragcut.py [id ...]  # $0: transparent drag-ghost silhouettes (run at every ingest; on-model→cloth-seg only, product→general)
```

The liminal-wardrobe venv (Python 3.9) has rembg/cv2/PIL; system python3 is 3.9 (no
`str | None` syntax). Headless design QA: Chrome `--headless=new --screenshot=…` then
actually look at the PNG.

## Queued next (do not build until asked)

- **CAROUSEL DETAIL GLASSMORPHISM EXPLORATION (requested 07-23):** when a look is
  clicked in the archive carousel, explore a glassmorphism treatment for the
  detail/preview panel that opens. Treat this as a visual-design study first,
  preserving the existing hero transition, legibility, and action hierarchy;
  do not ship it until Janice reviews the direction.
- **FULL SPIN BATCH (approved, HOLDING):** 58 garments + 18 outfits × ~$0.313 ≈
  $23.79 via `tryon.py … --spin`. Fire when Janice's back photos arrive (she's
  sourcing per the 07-19 priority list — A: distinct backs, B: shoe heel views,
  C: skippable symmetric basics) OR on her explicit "fire anyway". Ingest incoming
  backs into each `garments/<id>/raw/` as `*_back.*`; QA one batch tranche before
  the next. Items still lacking backs render invented rears — flag them for QA.
- **Pose rollout DONE** — going forward: one pose per saved look at creation
  (~$0.06/render). Do NOT re-pose via nb2/edit prompt language alone. Difficulty-4/5
  garments stay on the front pose (check `difficulty` in meta.json, not folder names).
- **Look cards, coverflow remainder:** the grid/index lens SHIPPED 07-19; any
  coverflow treatment from `~/liminal-wardrobe-v2/spec/design/CARD-PIPELINE.md`
  remains available if she ever wants a third lens.
- Sourcing notes: source-photo bar ≥1500px long side, ghost-mannequin/flat-lay >
  on-model > editorial; grab BACK views (spin rears use them as ground truth).
  Dropped items live in `garments/raw/_discarded/`, re-sourceable any time.
