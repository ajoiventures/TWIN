# Offline event replay — initial implementation

Implemented October 28, 2026 for #28 and the recorded-observation prerequisite of #29. This is a local deterministic event reducer; no camera feed, inference model, calibrated parking count or live service is connected.

`tools/event_replay.py` accepts a JSON array of events and the active semantic registry. Every event needs `event_id`, `entity_id`, `source_snapshot`, `mode`, `source_id`, `event_time`, `ingested_time`, `metric`, numeric `value`, `unit`, `confidence` in [0,1], and `evidence_ref`. Observed events require `sensor_id`; simulated/synthetic events require `run_id`. Times require explicit timezones and ingestion cannot precede the event. Entity membership and snapshot must match the registry. Evidence references and sensor IDs are required provenance labels, not proof of source access, valid calibration or trustworthy measurements.

Example invocation after authorized event data is available:

```powershell
python tools/event_replay.py data/observations/events.json --at 2026-10-28T16:00:00Z --known-at 2026-10-28T16:05:00Z --mode observed --stale-after 300 --output data/processed/event_replay.json
```

The input path above is an expected future input, not a supplied real dataset. Unit-test events are artificial fixtures only.

Replay selects events occurring by `--at` and received by `--known-at` (defaults to `--at`). This distinguishes retrospective reconstruction from what was known at the time. Exact duplicate records are idempotent; conflicting reuse of an event ID fails the entire input. Sorting uses event time then event ID, making results independent of arrival order. A same-time tie is deterministic, not a claim of causal precedence. Latest states remain separate by entity, source, sensor, run, metric and unit; the tool does not silently fuse different measurements. Each result includes input and registry hashes.

Only one explicit mode is replayed. Staleness uses observation age, not arrival time, so late data cannot masquerade as fresh. Empty rows mean no eligible evidence, not zero vehicles, zero demand or an available parking space. The reducer supports latest scalar measurements; it does not calculate vehicle trajectories, occupancy intervals, cumulative totals, availability or alerts by summing arbitrary events.

Verified: four focused tests cover shuffled/late arrival, exact/conflicting duplicates, knowledge cutoffs, unknown entity/snapshot, missing timezones, invalid values/confidence, future events, mode/source isolation and stale results. These tests establish reducer behavior, not real-world analytic accuracy.

Remaining #28/#29 work includes a reviewed sensor/run registry, real authorized input adapter, calibrated geographic association, metric-specific reducers, replay UI/API, scenario comparison, evaluation data, operational health and live-feed acceptance. Existing building identities do not establish space-level parking geometry; the parking inventory remains a prerequisite for parking availability claims.
