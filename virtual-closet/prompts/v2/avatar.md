# Avatar generation — v2 (learned fixes from Phase 2 round 1)

**Model:** `fal-ai/nano-banana-pro`. **Attachments:** Images 1–3 persona face (front, 3/4L, 3/4R), Image 4 full-body proportions ref.

## Changelog vs v1 (each clause earned by a failure)

| Fix | Failure it corrects |
|---|---|
| "Keep her styled, made-up look; do not plainify" (replaces v1's "natural skin texture / no retouching") | v1 candidates converged to a plainer face — the anti-beautify language fought the persona's glam styling |
| "fair, light East Asian complexion — pale but natural, NOT porcelain white" + "do not change her ethnicity" | "porcelain-pale, cool undertone" turned the avatar white/gothic (edit3-nbpro) |
| Eye color restated in every prompt: "dark brown, so deep they are nearly black" | edit3-nbpro drifted eyes to gray-green when omitted |
| "do not make the body curvier than Image 4; small bust (34A)" | edit1 inherited the persona refs' fuller bust |
| "One single … photograph of ONE woman — not a collage, not side-by-side panels" | edit4 returned a diptych |
| "swept gently to one side as in Image 1, moderate volume" | edit1 hair came out much fuller than requested |

## Template

> One single full-body studio photograph of ONE young East Asian woman (a single figure — not a collage, not side-by-side panels, not a comparison sheet). Face: exactly the woman in Images 1–3 — identical East Asian facial features, identical eye shape with her subtle winged eyeliner, identical fuller lips, identical nose and face proportions. Keep her styled, made-up look from the references; do not plainify, average, or change her ethnicity. Eyes: dark brown, so deep they are nearly black. Hair: black, slightly wavy, full bangs, worn down about 4 inches past her shoulders, swept gently to one side as in Image 1, moderate volume. Skin: fair, light East Asian complexion — pale but natural, NOT porcelain white. Body: petite 5ft3in, slender (~110 lbs), small bust (34A), 25-inch waist, narrow hips with a subtle curve, legs proportionally long — proportions as in Image 4; do not make the body curvier than Image 4. Clean unmarked skin, no tattoos. Standing naturally, arms relaxed at sides, five visible fingers on each hand, bare feet visible in frame. Wearing a plain heather-gray fitted scoop-neck tank top and black leggings. Plain light-gray seamless studio background, soft even neutral lighting, 50mm lens, photorealistic.

## Character sheet views (unchanged from v1, but restate the eye-color, skin, and single-figure clauses each time)
