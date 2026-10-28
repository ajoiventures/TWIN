# Semantic registry and scene inspection

The local `college-park-evidence-visualization/1.0` profile supports #26 without claiming NVIDIA certification or physical/survey accuracy.

`tools/semantic_registry.py` derives building-group identity from sorted original OCPA footprint object IDs, independent of list order and local mesh numbering. A membership change creates a new group identity. Parcels remain separate one-to-many relationships; spatial-only associations stay unaccepted. Records retain snapshot, source-file hash, height method, current-validity unknowns, historical acquisition interval where applicable and evidence references. Existing tree/car assets remain illustrative and are not given false official identity.

`tools/connect_scene.py` composes the additive semantic layer under manual edits. `tools/validate_scene.py` reads the final assembly, checks exact registry coverage, source/evidence hashes, active snapshot, identity/profile metadata, meter/Z-up conventions, finite mesh points, topology indices, building-height agreement and unresolved references. Instance proxies are included. It does not author repairs into sources.

Generated outputs stay local in `data/processed/asset_registry.json`, `asset_registry_quality.json`, `scene_validation.json` and `scene/semantic_assets.usda`. API routes `/api/v1/assets`, `/api/v1/asset_quality`, `/api/v1/scene_validation` expose these artifacts. Asset and height routes reject a mismatched active snapshot with HTTP 409. Building responses include entity/evidence IDs when current registry evidence exists.

Run `python tools/semantic_registry.py`, `python tools/connect_scene.py`, `python tools/validate_scene.py`. Re-run after snapshot or height changes. Source files and manual edits remain separate; a validator pass does not imply they are all correct or reviewed.

Remaining #26 work: evaluate supported NVIDIA libraries on an isolated scene copy, pin runtime/profile compatibility, visual preflight evidence, city task-specific collision/material/traversability checks where required, safe repair workflow and independent acceptance. No SDK update has been performed by these tools.
