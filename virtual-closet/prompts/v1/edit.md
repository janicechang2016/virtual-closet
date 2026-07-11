# Corrective edit — v1

**Model:** same model that produced the render being edited. **Attachment:** previous best render (Image 1); garment or face reference re-attached only when the correction concerns it.

## Template

> Edit this image only as follows: {single_specific_correction}. Keep the face, body, pose, lighting, and everything else exactly unchanged.

**Rules:** one correction per edit call; max 4 sequential edits per lineage (identity degrades past ~5) — then restart from candidates with learned prompt fixes.

## Canned corrections (feedback-button taxonomy → edit prompt)

| Button | Edit instruction |
|---|---|
| `wrong fit` | "adjust the garment fit to {fit from meta.json}; the cut should read as {fit} on this body" |
| `fabric off` | "re-render the garment fabric as {fabric}: correct sheen, weight, and drape for that material" |
| `face drifted` | "restore the face to exactly match the attached character reference — features, asymmetries, and skin texture" |
| `artifact` | "fix the {location} region: {artifact description from QA}; anatomically correct hands with five fingers" |
| `pattern wrong` | "correct the garment's pattern to match the attached garment photo exactly, including placement and alignment at seams" |
