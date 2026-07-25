# V4 face references — Gemini

Gemini is the selected source for the v3 facial turnaround references.
ChatGPT image outputs were rejected because the generated facial geometry and
identity drifted too far from v3.

Keep the original, highest-resolution downloads in this folder. Preferred
filenames:

- `v3-face-front.png`
- `v3-face-three-quarter-right.png`
- `v3-face-three-quarter-left.png`
- `v3-face-profile-right.png`
- `v3-face-profile-left.png`
- `v3-face-eyes-detail.png`
- `v3-face-nose-mouth-detail.png`

Do not overwrite the canonical v3 image or the approved v4 Blender checkpoint.
These images are sculpting references only.

## Locked reference hierarchy

- `v3-face-front.png` — immutable identity and proportion master
- `right-threequarter.png` — secondary transitional-volume reference
- `left-profile.png` — secondary depth reference; mirror for the other side
- `v3-face-eyes-crop.png` — exact crop of the identity master
- `v3-face-nose-mouth-crop.png` — exact crop of the identity master

`left-threequarter.png` and `right-profile.png` remain advisory only because
Gemini introduced visible identity or angle drift. Ignore generated moles,
pores, skin marks, and cross-view asymmetry.
