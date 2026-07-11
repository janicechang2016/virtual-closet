# Try-on compose — v1

**Model:** Nano Banana 2 (default; Phase 3 benchmark may change this). **Attachments:** Images 1–4 = character sheet views, Image 5 = garment photo.

## Template

> Dress the person from Images 1–4 (character reference — keep face, hair, body proportions identical) in the garment shown in Image 5. Reproduce the garment exactly: same color, pattern placement, neckline, sleeve length, buttons, and any text or logos. Natural fabric drape appropriate to {fabric}. Same studio background and lighting as the reference images. Full-body, front-facing.

Substitutions from `garments/<id>/meta.json`: `{fabric}`; append `details_to_preserve` as "Pay particular attention to: …" when non-empty.

## Layering (Phase 5)

Sequential edits, base-out: render layer_order 0 garment first, then edit-prompt each higher layer onto the previous render (see `edit.md`).
