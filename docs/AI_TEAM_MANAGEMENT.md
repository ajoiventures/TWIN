# AI team operating plan — College Park TWIN

Updated October 28, 2026. AI roles are task responsibilities, not human corporate appointments or continuously running employees. Actual GitHub assignees are unchanged. Three bounded management/technical review agents have completed their initial reviews; execution agents are instantiated when a work batch starts. No recurring automation is configured.

## Current owner instructions — October 28, 2026

Keep the highest quality and gain speed through parallel ticket execution. During a build batch, the integrator can coordinate three independent builders within the four available slots. Consolidate independent review after every five completed tickets; assign a reviewer who did not implement the work under review. Necessary local construction checks continue. Full tickets, partial features, and building candidates are counted separately. This cadence supersedes older per-change review sequencing below.

Apply the [all-building exception process](EDGEWATER_PROPERTY_AUDIT.md#repeatable-missing-building-process--full-project) across the full Main Street and neighborhood coverage ledger, including all uses and missing upper floors. One showcase property must not hold corridor-wide building, sidewalk, road, parking or asset delivery.

## Learning and reusable scripts

Apply the [learning and script creation protocol](protocols/LEARNING_AND_SCRIPT_CREATION.md) with the [College Park profile](COLLEGE_PARK_PROTOCOL_PROFILE.md). Builders search existing helpers before creating scripts; analysts record source semantics; independent reviewers check the actual result; PM links reusable lessons to tickets; Director resolves acceptance conflicts. VP reviews strategic tradeoffs, not every script. Use proportional records and existing evidence to avoid slowing execution. Repository `AGENTS.md` points future agents to this workflow.

## Leadership

## Distinct management levels and reporting line

Human owner → VP/Sponsor Agent → Delivery Director Agent → Project Manager Agent → delivery workstreams. These are separate responsibilities and authority levels. A tool agent previously named `pm_director` is a legacy combined task name; it does not establish a combined management position. Future management assignments must explicitly name which role is acting.

| Level | Decisions and accountability | Escalation |
|---|---|---|
| VP / Sponsor | Project value, major scope/resource recommendations and executive risk review; presents decisions to the human owner | Spending, publication, commitments and major scope decisions remain with the human owner |
| Delivery Director | Oversees the PM and technical delivery; resolves cross-workstream priorities, assigns integration capacity and accepts/rejects delivery gates using lead/independent QA evidence | Escalates strategic scope/resource conflicts to VP; returns incomplete work to PM with concrete criteria |
| Project Manager | Reports to Director; maintains ticket scope, sequencing, dependencies, responsible roles, ready queue, blockers, evidence and accurate status | Escalates unresolved delivery conflicts and readiness decisions to Director; cannot waive quality gates or self-approve completion |
| Technical leads / workstreams | Execute and review domain work; provide source, geometry, test and render evidence | Bring domain conflicts to PM for coordination and Director for decisions when needed |

PM reports progress; Director judges delivery readiness. Independent QA supplies an independent assessment, and neither management level may substitute a status report for actual acceptance evidence. Role separation applies even when limited agent capacity means one bounded execution agent performs tasks at different times; it must state which role it is performing and cannot manufacture an independent review of its own work.

| Role | Responsibility |
|---|---|
| Project Manager Agent | Own roadmap #14, ready queue, dependencies, blocker log, evidence links and status accuracy. |
| Delivery Director Agent | Own delivery quality, cross-workstream decisions, readiness and acceptance gates. |
| VP/Sponsor Agent | Recommend scope/value tradeoffs and first-delivery priorities; review major risks rather than every ticket. Human owner retains final authority. |
| GIS/Data Analyst Agent | Own source coverage, dates, schemas, units, joins, exceptions and safe previews. |
| Technical leads | GIS lead reviews geographic/data evidence; 3D lead reviews geometry, USD composition, placement and performance. |
| Independent QA Agent | Review evidence in a separate pass and report unresolved findings. The sole implementer cannot claim independent self-review. |

## Ticket ownership

## Full-project delivery team — current operating model

The owner requested coverage of the full project and faster execution through efficiency. This section supersedes the initial pilot staffing/dispatch notes below. Scope remains all College Park Main Street in detail, the wider neighborhood context, accurate buildings/roads/sidewalks/parking/parks, professional visuals, planning scenarios and validated live operations. Management positions are separate levels; the number of role names does not create extra concurrent workers.

| Workstream / lead responsibility | Full-project deliverables | Existing tickets |
|---|---|---|
| GIS / property data lead | Authoritative sources, parcel/building identity, complete corridor inventory, safe API/schema previews, source dates and exception queues | #2–5, #12, #19, #20, #22 |
| Planning / land analyst | Exact zoning/overlays/FLU/PD conditions, government ownership, vacancy and development constraints; distinguish entitlement from actual use | #3–5, #14, #21, #22, #25 |
| Civil / transportation lead | Road edges/intersections, continuous sidewalks and ramps, crossings, parking/access/loading, transit and signed engineering evidence | #15–17, #21, #25 |
| Architectural reconstruction lead | Missing commercial/civic/religious/multifamily buildings, roofs/wings/upper floors, recognizable façades and current/historical/construction distinctions | #3, #6, #8, #17, #20, #32 |
| Environment / rendering lead | Tree-lined street views, realistic varied trees/cars, parks, physical-scale materials, lighting, cameras and actual render quality | #8–10, #17, #18 |
| Terrain / environmental GIS lead | DEM/datum/anchoring, water, land cover and effective flood context with correct limitations | #6, #23, #24 |
| Commercial reference analyst | Verified property/suite/business/listing relationships, dated broker/operator evidence, storefront reference and approved BOOMS linkage | #7, #8, #32 |
| Simulation / mobility analyst | Existing/proposed comparisons, reproducible runs, parking/access/shade metrics and calibrated mobility when observations support it | #15, #21, #28 |
| NVIDIA / platform engineer | Reproducible OpenUSD composition, semantic assets, grounded query/replay, suitable NuRec/VSS trials, authorized operations and measured orchestration needs | #1, #12, #26–30 |
| Independent QA / release reviewer | Source/geometry exceptions, same-view rendered comparison, source freshness, fresh launch, conference performance and acceptance evidence | #11, #13; reviews all workstreams |

Domain leads are accountable for their technical evidence; independent QA tests it. PM coordinates the integrated backlog; Director owns cross-stream decisions and delivery acceptance; VP reviews strategic value/resource issues at milestones. External spending, publication and other reserved decisions remain with the human owner.

### Four-slot execution pattern

1. **Integrator:** primary agent integrates source/scene/API changes, runs affected checks and maintains the concrete result. It performs bounded Director decisions when needed; that does not constitute independent QA of its own implementation.
2. **Builder A:** one bounded architectural/geometry or data package, with an explicit file boundary and deliverable.
3. **Builder B:** one independent civil/sidewalk/parking, asset, source or platform package selected from the ready queue. It must not write Builder A's files or trigger duplicate source acquisition.
4. **Independent reviewer:** review the actual current artifact and targeted evidence; identify blocking defects early and review the final changed version. QA is a function distinct from the VP role, even if a legacy agent task name mentions VP.

These are capacity slots, not permanently staffed people. Select the needed specialist capability for each batch. PM/Director/VP decisions are lightweight responsibilities exercised at defined points, not three mandatory always-running management agents or approval steps on every reversible change.

### Efficiency rules

- One canonical GitHub backlog (#14 coordinates), one documentation index, one versioned source/identity registry and shared cached evidence. Update an existing ticket/package instead of creating a duplicate plan or repeating discovery.
- Ready work names the exact output, dependencies, files, reviewer and acceptance evidence. Begin implementation when enough evidence exists; keep unknowns visible rather than waiting for every source or every ticket to close.
- Limit work in progress to the two builders. Parallelize independent tasks; keep composition, source activation and shared-file edits under the integrator. Do not run simultaneous scene mutations during a captured comparison.
- Work by coherent block or feature package, then reuse accepted geometry/material/reference methods along the full corridor. A pilot proves a method; it never reduces the final scope.
- Reuse original data/receipts and perform incremental rebuilds. Fetch new source bytes only for a demonstrated gap or freshness need. A material/camera change must not rebuild the district or reacquire parcels.
- Run targeted checks as work changes; run the required broader integration/release checks at the appropriate gate. Repeat a render/test only for a changed input, failure, new finding or unverified deliverable. Tests passing never replace visual review.
- PM updates status at batch boundaries and escalates only concrete conflicts. Director resolves integration/quality conflicts; VP handles milestone scope/value/resource issues. Routine reversible implementation continues within authorized scope.
- Prefer a small finished, independently reviewed result over more planning documents. Planning additions requested by the owner remain tracked, but must feed a ready implementation queue.
- Track actual cycle time, review turnaround, reopened defects, repeated downloads/rebuilds and accepted corridor coverage. Use observed throughput for estimates; no invented deadlines, utilization claims or speed guarantees.
- Done requires the ticket's full acceptance evidence. Source packets, provisional reconstructions and accepted final visuals are different states. Faster delivery must preserve accuracy, independent review, source rights and rollback.

### Current priority sequence

Run the full-corridor building/upper-floor exception process, continuous sidewalk/road/rear-parking corrections, and district-wide tree/car asset improvements in parallel. Reuse the finished office draft and earlier Princeton/Wellesley methods without concentrating the team on one property. Expand the inventory beyond commercial screening and beyond the current extraction where neighborhood context is not covered. Terrain, parks/public land, planning and operations retain their requirements. Consolidate independent review after five completed tickets; retain explicit evidence gaps while other ready blocks continue.

| Issue | Responsible AI role | Accountable role | Reviewer | Required capabilities | Skill playbooks |
|---|---|---|---|---|---|
| [#1](https://github.com/ajoiventures/TWIN/issues/1) | Platform Engineer | Delivery Director | QA Engineer | portable setup, USD composition, dependency management | engineering:architecture; engineering:testing-strategy |
| [#2](https://github.com/ajoiventures/TWIN/issues/2) | GIS/Data Analyst | GIS Technical Lead | QA Analyst | data profiling, reconciliation, publication allowlists | data:explore-data; data:validate-data |
| [#3](https://github.com/ajoiventures/TWIN/issues/3) | GIS Data Engineer | GIS Technical Lead | GIS/Data Analyst | ArcGIS adapters, parcel identity, spatial joins | data:validate-data; engineering:testing-strategy |
| [#4](https://github.com/ajoiventures/TWIN/issues/4) | GIS Data Engineer | GIS Technical Lead | GIS/Data Analyst | ArcGIS/Socrata ingestion, schemas, source coverage | data:explore-data; data:validate-data |
| [#5](https://github.com/ajoiventures/TWIN/issues/5) | GIS/Data Analyst | GIS Technical Lead | QA Analyst | boundary reconciliation, CRS, entity identity | data:validate-data |
| [#6](https://github.com/ajoiventures/TWIN/issues/6) | LiDAR/Terrain Engineer | GIS Technical Lead | QA Analyst | point classification, vertical datums, roof/ground estimates | data:validate-data; engineering:testing-strategy |
| [#7](https://github.com/ajoiventures/TWIN/issues/7) | GIS/Data Analyst | Delivery Director | Data Release Reviewer | BOOMS linkage, release gates, privacy field selection | data:explore-data; data:validate-data |
| [#8](https://github.com/ajoiventures/TWIN/issues/8) | Reference Analyst | 3D Technical Lead | GIS/Data Analyst | dated facade evidence, asset rights, storefront identity | data:validate-data |
| [#9](https://github.com/ajoiventures/TWIN/issues/9) | Vegetation/3D Artist | 3D Technical Lead | GIS/Data Analyst | canopy evidence, species uncertainty, USD instancing, clearance | engineering:testing-strategy |
| [#10](https://github.com/ajoiventures/TWIN/issues/10) | Vehicle/3D Artist | 3D Technical Lead | Transportation Analyst | vehicle scale/materials, parking geometry, instancing | engineering:testing-strategy |
| [#11](https://github.com/ajoiventures/TWIN/issues/11) | Environment Artist | 3D Technical Lead | QA Analyst | facade modeling, reference alignment, pedestrian space | engineering:testing-strategy |
| [#12](https://github.com/ajoiventures/TWIN/issues/12) | Application Engineer | Delivery Director | QA Engineer | provenance UX, snapshot rollback, layer controls | engineering:testing-strategy; design:ux-copy |
| [#13](https://github.com/ajoiventures/TWIN/issues/13) | QA Engineer | Delivery Director | GIS Technical Lead and 3D Technical Lead | geographic QA, fixed cameras, performance profiling | engineering:testing-strategy; data:validate-data |
| [#14](https://github.com/ajoiventures/TWIN/issues/14) | Project Manager | Delivery Director | VP/Sponsor Agent | dependency management, capacity, scope and decisions | product-management:sprint-planning; product-management:roadmap-update |
| [#15](https://github.com/ajoiventures/TWIN/issues/15) | Transportation Data Engineer | GIS Technical Lead | Transportation Analyst | RCI linear referencing, GTFS, temporal/spatial joins | data:validate-data |
| [#16](https://github.com/ajoiventures/TWIN/issues/16) | Transportation GIS Analyst | GIS Technical Lead | QA Analyst | actual pedestrian geometry, statuses, topology | data:validate-data |
| [#17](https://github.com/ajoiventures/TWIN/issues/17) | Civil/3D Geometry Engineer | 3D Technical Lead | Transportation GIS Analyst | curb/sidewalk geometry, alignment, topology, clearances | engineering:testing-strategy; data:validate-data |
| [#18](https://github.com/ajoiventures/TWIN/issues/18) | Environment Artist | 3D Technical Lead | QA Engineer | materials, realistic placement, fixed-camera QA, optimization | engineering:testing-strategy |
| [#19](https://github.com/ajoiventures/TWIN/issues/19) | Source Research Analyst | GIS Technical Lead | GIS/Data Analyst | metadata, coverage, acquisition deduplication | data:explore-data; data:validate-data |
| [#20](https://github.com/ajoiventures/TWIN/issues/20) | Imagery/GIS Analyst | GIS Technical Lead | Reference Analyst | dated aerial change review, discrepancy mapping | data:validate-data |
| [#21](https://github.com/ajoiventures/TWIN/issues/21) | Scenario/3D Engineer | 3D Technical Lead | Transportation GIS Analyst | design revision tracking, future layer isolation | engineering:testing-strategy |
| [#22](https://github.com/ajoiventures/TWIN/issues/22) | GIS Data Engineer | GIS Technical Lead | GIS/Data Analyst | County/City stewardship, public coverage and joins | data:explore-data; data:validate-data |
| [#23](https://github.com/ajoiventures/TWIN/issues/23) | Environmental GIS Analyst | GIS Technical Lead | QA Analyst | hydrography, land cover, terrain intersections | data:validate-data |
| [#24](https://github.com/ajoiventures/TWIN/issues/24) | Hazard GIS Analyst | GIS Technical Lead | QA Analyst | effective flood-map metadata and correct interpretation | data:validate-data |
| [#25](https://github.com/ajoiventures/TWIN/issues/25) | Engineering Records Analyst | GIS Technical Lead | Transportation GIS Analyst | plan/as-built evidence, georeferencing, designed/built status | data:validate-data |

Skill names identify available playbooks to read when applicable, not skills already executed or certified qualifications. The management pass used the sprint-planning workflow.

## Operating rules

- Workflow: Backlog → Ready → In progress → Review → Done. Blocked carries exact dependency, next action and responsible role.
- Ready: bounded deliverable, source/write boundary, prerequisite artifact/version, responsible owner, separate reviewer and testable acceptance criteria. Source-access research can be Ready while later geometry remains dependency-blocked.
- Capacity: four available concurrent agent slots; reserve the primary for integration. Use at most two implementation workstreams plus one independent review. Role count is not capacity. Do not promise dates without a capacity assessment.
- Done: acceptance evidence attached, appropriate tests passed, critical findings resolved, source/date/quality labels visible and rollback/manual edits preserved. Discovery completion does not imply acquisition or modeled geometry completion.
- Reporting: PM refreshes status at work-batch boundaries; Director reviews gate evidence; VP reviews scope exceptions and first-delivery results. No automatic recurring status messages or background work are implied.
- Escalation: routine reversible work proceeds. Human decisions are needed for spending, external outreach, publication of held data, irreversible actions, and material scope/budget/deadline commitments.
- Use GitHub issue numbers as canonical IDs because legacy TWIN IDs differ.

## Historical initial ready batch

1. #19: Source Research Analyst produces catalog, actual coverage/access tests and acquisition-deduplication decisions. This discovery task need not wait for all of #3/#4 to close.
2. #3: GIS Data Engineer audits parcel/building exceptions, floor conflicts, multi-building parcels, stable links and timestamp provenance; GIS Analyst reviews the evidence.
3. #16: Transportation GIS Analyst performs bounded pedestrian-source access discovery; exact public endpoints/gaps and request drafts are outputs. It can run before all of #15 closes; geometry acceptance still needs aligned street evidence.

Dispatch only within capacity; the three reviews in this management pass do not mean those implementation tasks have started. Freeze pilot endpoints/reference date under #5/#17 before property-by-property #20 review. Start bounded #6 source/unit assessment at P0, then terrain expansion after accepted geographic/vertical evidence. Finish #17 geometry before #18 placement sign-off.

## Historical initial delivery proposal

One named continuous Edgewater block with dated parcel/building references, traceable heights, a bounded terrain tile, confidence visible in the inspector, a sidewalk/parking gap map, and fixed-camera/performance evidence. Missing widths and slopes stay unknown; source discovery alone does not establish surveyed accuracy.

Defer #21 future design and #23/#24 optional overlays until existing conditions are accepted. Limit #22/#25 to pilot-critical sources. Existing features, historical measurements, estimates and proposed geometry remain distinct.

## Historical initial review findings

- Current work is connected locally and partially implemented, not accepted complete. Ninety historical LiDAR heights and 3,000 estimates do not establish district-wide measured heights; ground is still flat.
- Review 196 spatial-only and 37 ambiguous/unmatched building groups before applying parcel-level assumptions. Multi-building parcels require one-to-many reasoning.
- Freeze boundary type, pilot extent, reference date, coordinate conventions and vertical datum before geometry sign-off. The extraction rectangle is not an official district boundary.
- The EPQS comparison supports unit sanity, not independent survey accuracy. Re-anchor roads/buildings/trees after terrain displacement.
- Architectural reference gathering #8 can proceed without private BOOMS release; business identity/context remains gated. Generic provenance #12 can proceed independently of BOOMS-specific views.
- Independent QA must cover geographic residuals, source metadata, actual pedestrian evidence, existing/future isolation, manual-edit preservation and measured performance at a stated resolution.

## Review participants

Initial bounded reviews included a legacy combined PM/Delivery Director task, GIS/Data Analyst and VP/Sponsor review tasks. The owner clarified that PM and Director are distinct levels. The legacy task name is not the current reporting structure; subsequent role assignments and acceptance follow the separate authority levels above. No claim that roles are permanently active.
