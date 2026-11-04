# College Park protocol profile

Applies the [reusable learning and script protocol](protocols/LEARNING_AND_SCRIPT_CREATION.md) to TWIN. Scope is all College Park Main Street, with the wider neighborhood context; Princeton–Edgewater is one component. The full ticket plan remains authoritative.

## Before implementation

Read [execution checkpoints](EXECUTION_STATUS.md), the actual ticket, [project index](INDEX.md) and relevant [lessons](LESSONS_LEARNED.md). Verify the current active snapshot, composed layers and working-tree changes. Search `tools/` for an existing adapter, reconstruction, activation or review helper. Use the [team responsibilities](AI_TEAM_MANAGEMENT.md); PM and Director are distinct roles.

## Data and modeling rules

- Keep parcel feature, source parcel number, building group, physical building, condo unit, storefront, business and listing identities distinct. Reuse the existing entity registry; source membership changes need reconciliation.
- Record publisher, stable source ID, URL, acquisition/effective/retrieval dates, CRS/units/vertical datum, coverage, reuse conditions and checksums. Use the newest applicable revision, retaining historical/proposed/current distinctions.
- Use immutable snapshots and guarded derived products. [Building lineage](BUILDING_LINEAGE.md) illustrates additive evidence without replacing an otherwise unchanged snapshot.
- Preserve manual USD layers, unsaved user edits and active Rhino/Omniverse sessions. A reviewer window can become the user's working window; re-observe before acting. Never infer that it is disposable from who launched it.
- Prepare geometry in a separate proposal. Inspect source fit, unsupported regions, topology, placement and an actual render before promotion. Keep unknown or approximate areas labeled; no parcel-envelope building, hidden curb, façade or roof-height inference from unsuitable evidence.
- Keep private BOOMS gates and imagery-use restrictions intact. Original aerial pixels and raw caches remain local unless actual authorization and source conditions permit otherwise.

## Delivery and review

Execute independent tickets in parallel with explicit file ownership. Review after each **five completed existing tickets**; five edits or five buildings are not five tickets. Continue necessary local checks. Latest recorded batch passed at five; verify live ticket state before deciding when the next batch is due.

Use current runtime paths and running-process evidence rather than hardcoding remembered process IDs. `tools/serve.py` supports `--port` and `--preserve-selection`; verify the selected port and service state. A denied restart is not permission to force termination. A separate read-only review service must not reset the user's shared selection.

For source/geometry changes, refresh only the dependent ledgers and validate their freshness. For visual work, capture the same camera and render settings before/after; record source and scene versions. Numerical residuals support geometric fit but cannot substitute for visual inspection or current-condition evidence.

A ticket closes only when its full acceptance scope is supported. Broader property verification, currentness, live operations and conference quality stay open when only a bounded data adapter or historical review has passed.
