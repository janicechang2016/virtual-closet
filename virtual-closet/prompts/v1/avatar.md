# Avatar generation — v1

**Model:** Nano Banana Pro (`fal-ai/nano-banana-pro` via fal). **Attachments:** 3–6 face reference photos (+ optional full-body photo as last image).

## Template

> Full-body studio photograph of the person in the reference images. Preserve facial features, asymmetries, and skin texture exactly as in the reference images — do not beautify or average the face. Body: {height}, {build_description}, natural posture, arms relaxed at sides, five visible fingers on each hand. Wearing a plain heather-gray fitted tank top and black leggings, barefoot. Plain light-gray seamless studio background, soft even lighting, 50mm lens, photorealistic, natural skin texture, no retouching look. Eyes: {eyes.color_exact_shade}. {distinctive_features_clause}

`{build_description}` is derived from `avatar/measurements.json` (shoulder-to-hip ratio, waist definition, self-description verbatim). `{distinctive_features_clause}` = "Preserve exactly: " + joined `distinctive_features`.

## Character sheet (after avatar approval)

Same prompt with the approved avatar attached as Image 1, varying only:
- "…identical person, camera at 3/4 left angle"
- "…identical person, camera at 3/4 right angle"
- "…identical person, viewed from behind"
- "…identical person, seated on a plain gray cube, hands resting on knees"

Same base outfit, background, lighting in all views.
