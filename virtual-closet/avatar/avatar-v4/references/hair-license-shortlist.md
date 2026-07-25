# Avatar v4 hair sourcing

Target: dark upper-bust hair with straight, light, wispy bangs; clean
front/profile/rear silhouette; distributable in the portfolio app.

## Rejected after visual/import test

- **Wolf Hair — Greedy Engine**
  - https://sketchfab.com/3d-models/wolf-hair-d9010cfd1f304ec7a0300a49f30d039a
  - Listing: CC BY; downloadable; 57.3k triangles / 40.1k vertices.
  - Creator describes it as a wolf cut with bangs.
  - Why it is plausible: original creator attribution is clear, the layered
    fringe does not form the opaque helmet edge seen in our procedural cards,
    and the mesh density is workable for a Blender source candidate.
  - Archive inspected and preserved under `wolf-hair/`. It contains three
    meshes and one active strand texture, with no linked libraries or executable
    content. The listing is the only license record; attribution is preserved.
  - Rejected visually after full orientation, crown-scale, depth, and material
    fit tests: this is an anime/card-shell cut with a tall scalp, heavy face
    cards, and fragmented alpha edges. It cannot meet the photoreal target.

## Rejected after visual/import test

- **Female hairs — miccall**
  - https://sketchfab.com/3d-models/female-hairs-0a391b6508a241f4b0b399f403ee4602
  - Listing: CC BY; downloadable; 51.1k triangles / 31.5k vertices.
  - Eight-style collection with realistic straight/mid-length and bob options.
  - Archive inspected and preserved under `female-hairs/`: eight meshes, eight
    packed textures, no linked libraries; only the irrelevant HDR environment
    is missing. Listing is the only license record.
  - Style 02 was selected as the closest straight upper-bust silhouette and
    fully normalized/fitted to candidate 08.
  - Rejected: its PNG has no alpha channel and the geometry uses broad beige
    face/scalp cards. Removing the central cards exposes coarse ribbon topology
    and scalp holes; darkening preserves the jagged strips. It cannot pass the
    photoreal or browser-transparency gate.

## Rejected during sourcing

- zHairezt/Zepeto-derived hair uploads: listing says CC BY, but the uploader
  explicitly credits Zepeto rather than claiming authorship. Do not use.
- Artemis ponytail: CC BY-NC and uncertain upstream material provenance. Do
  not use for the distributable app.
- Culturalibre hair 01: AGPL-3 in the source `.mhclo`. Already rejected.
- Current MPFB long hair + extracted fringe: valid as the approved foundation
  placeholder, but fails face integration by covering one eye and reads too
  long/heavy for the requested art direction.

No external hair asset is approved merely by appearing in this list.
