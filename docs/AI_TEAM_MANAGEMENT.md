# AI team operating plan — College Park TWIN

Updated October 28, 2026. AI roles are task responsibilities, not human corporate appointments or continuously running employees. Actual GitHub assignees are unchanged. Three bounded management/technical review agents have completed their initial reviews; execution agents are instantiated when a work batch starts. No recurring automation is configured.

## Leadership

| Role | Responsibility |
|---|---|
| Project Manager Agent | Own roadmap #14, ready queue, dependencies, blocker log, evidence links and status accuracy. |
| Delivery Director Agent | Own delivery quality, cross-workstream decisions, readiness and acceptance gates. |
| VP/Sponsor Agent | Recommend scope/value tradeoffs and first-delivery priorities; review major risks rather than every ticket. Human owner retains final authority. |
| GIS/Data Analyst Agent | Own source coverage, dates, schemas, units, joins, exceptions and safe previews. |
| Technical leads | GIS lead reviews geographic/data evidence; 3D lead reviews geometry, USD composition, placement and performance. |
| Independent QA Agent | Review evidence in a separate pass and report unresolved findings. The sole implementer cannot claim independent self-review. |

## Ticket ownership

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

## First ready batch

1. #19: Source Research Analyst produces catalog, actual coverage/access tests and acquisition-deduplication decisions. This discovery task need not wait for all of #3/#4 to close.
2. #3: GIS Data Engineer audits parcel/building exceptions, floor conflicts, multi-building parcels, stable links and timestamp provenance; GIS Analyst reviews the evidence.
3. #16: Transportation GIS Analyst performs bounded pedestrian-source access discovery; exact public endpoints/gaps and request drafts are outputs. It can run before all of #15 closes; geometry acceptance still needs aligned street evidence.

Dispatch only within capacity; the three reviews in this management pass do not mean those implementation tasks have started. Freeze pilot endpoints/reference date under #5/#17 before property-by-property #20 review. Start bounded #6 source/unit assessment at P0, then terrain expansion after accepted geographic/vertical evidence. Finish #17 geometry before #18 placement sign-off.

## First delivery

One named continuous Edgewater block with dated parcel/building references, traceable heights, a bounded terrain tile, confidence visible in the inspector, a sidewalk/parking gap map, and fixed-camera/performance evidence. Missing widths and slopes stay unknown; source discovery alone does not establish surveyed accuracy.

Defer #21 future design and #23/#24 optional overlays until existing conditions are accepted. Limit #22/#25 to pilot-critical sources. Existing features, historical measurements, estimates and proposed geometry remain distinct.

## Initial review findings

- Current work is connected locally and partially implemented, not accepted complete. Ninety historical LiDAR heights and 3,000 estimates do not establish district-wide measured heights; ground is still flat.
- Review 196 spatial-only and 37 ambiguous/unmatched building groups before applying parcel-level assumptions. Multi-building parcels require one-to-many reasoning.
- Freeze boundary type, pilot extent, reference date, coordinate conventions and vertical datum before geometry sign-off. The extraction rectangle is not an official district boundary.
- The EPQS comparison supports unit sanity, not independent survey accuracy. Re-anchor roads/buildings/trees after terrain displacement.
- Architectural reference gathering #8 can proceed without private BOOMS release; business identity/context remains gated. Generic provenance #12 can proceed independently of BOOMS-specific views.
- Independent QA must cover geographic residuals, source metadata, actual pedestrian evidence, existing/future isolation, manual-edit preservation and measured performance at a stated resolution.

## Review participants

Initial bounded reviews completed by PM/Delivery Director agent, GIS/Data Analyst agent and VP/Sponsor review agent. Their recommendations are incorporated here; no claim that they are permanently active.
