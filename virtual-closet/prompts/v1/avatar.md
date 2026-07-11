# Avatar generation — v1 (persona-face variant)

**Model:** Nano Banana Pro (`fal-ai/nano-banana-pro` via fal).
**Attachments, in order:** Image 1 = `front face.png`, Image 2 = `left face.jpeg`, Image 3 = `right face.jpeg` (persona face), Image 4 = `full-body-upright.jpeg` (proportions ONLY — its face/skin markings are not canon).

> Identity is split by design (see `docs/decisions.md`): face comes from Images 1–3, body proportions from Image 4 + measurements. Prompts must bind each explicitly or the model will blend identities.

## Candidate template

> Full-body studio photograph of a young woman. **Face and hair:** exactly the woman in Images 1–3 — same facial features, same dark brown (nearly black) eyes, same black slightly wavy hair with full bangs, worn down about 4 inches past her shoulders. Do not alter or average her face. **Body:** petite 5'3" East Asian woman, slender (~110 lbs), not very curvy, 25-inch waist, subtle hip curve, legs proportionally long for her height — proportions as in Image 4. Pale skin tone, clean unmarked skin with no tattoos. Natural posture, arms relaxed at sides, five visible fingers on each hand. Wearing a plain heather-gray fitted tank top and black leggings, barefoot. Plain light-gray seamless studio background, soft even neutral lighting (not warm), 50mm lens, photorealistic, natural skin texture. Eyes: dark brown, nearly black.

Notes:
- "soft even **neutral** lighting (not warm)" counteracts the warm cast baked into the persona refs.
- "clean unmarked skin with no tattoos" is required in **every** prompt that shows arms/legs — Image 4 contains tattoos the avatar must not inherit.

## Character sheet (after avatar approval)

Approved avatar attached as Image 1; vary only:
- "…identical person, camera at 3/4 left angle"
- "…identical person, camera at 3/4 right angle"
- "…identical person, viewed from behind"
- "…identical person, seated on a plain gray cube, hands resting on knees"

Same base outfit, background, lighting in all views. Re-state the clean-skin and eye-color clauses each time.
