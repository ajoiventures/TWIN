# Learning and script creation protocol

Version 1 · October 29, 2026 UTC · Reusable across projects

Use this protocol to finish work faster without repeating mistakes or losing source evidence. Apply the reusable rules below, then the project's own scope, acceptance criteria and operating constraints. The [College Park profile](../COLLEGE_PARK_PROTOCOL_PROFILE.md) is one implementation, not a restriction on reuse elsewhere.

## The operating loop

**Retrieve → establish the baseline → implement → verify the result → record the lesson → reuse.**

Before starting, read the current ticket, latest applicable checkpoint and relevant lessons. Inspect the actual files and runtime; a prior success report does not prove the current state. Search existing scripts before creating another. Record the concrete outcome and the evidence that will demonstrate it.

Use the newest applicable evidence, not merely the newest download. Keep observation/acquisition, effective date, publication, retrieval and build dates distinct. A newer proposal cannot silently replace existing conditions. Leave unknowns explicit.

After meaningful work, record what changed, the result actually observed, any remaining limitation and the reusable decision. Learning means updating persistent project records and reusable implementations; it does **not** mean model retraining, unlimited memory or unattended monitoring.

## A proportionate record

| Work | Minimum record | Verification |
|---|---|---|
| Small reversible edit or disposable read-only inspection | Ticket/checkpoint note; no separate process document | Inspect the changed result |
| Repeated transformation, data adapter or production script | [Script contract](../templates/SCRIPT_CONTRACT.md), which may be a section in an existing document | Representative real input plus relevant failure/replay cases |
| Source/geometry promotion, shared-state change or release | Contract, candidate artifact, dependencies, preservation/rollback evidence and independent review | Actual affected output at the requested scope |

Do not turn every correction into a new ticket or test suite. Reuse fixtures and review records. Add a test when it catches a consequential failure, not simply to mirror the implementation. Repeat checks only after a relevant change, failure or unresolved concern.

## Learning records

Use the [lesson template](../templates/LESSON_RECORD.md). Record a lesson when a failure recurs, a significant assumption is disproved, or a successful method is reusable. Keep one authoritative entry; link to it instead of copying it into many documents.

1. **Observed:** describe the trigger and attach actual evidence. Separate symptoms from inferred causes.
2. **Candidate:** propose a bounded rule or fix. Do not present an untested hypothesis as established knowledge.
3. **Verified:** reproduce the relevant case and inspect the result. Record where the rule applies and where it does not.
4. **Adopted:** update the shared helper, template, project instructions or reference document that future work actually uses.
5. **Superseded:** retain the old record with a replacement link and reason when later evidence changes the conclusion.

Each lesson needs an ID, date, context, evidence, decision, applicability limits, owner role, reviewer where required and adoption location. Redact secrets and private source records. A lesson cannot grant new access, licensing, publication rights or permission to contact others. Tool approval rejection is recorded as returned; never invent a reason or work around a rejected operation through an equivalent command.

## Script creation and reuse

### 1. Define the contract before coding

State the user-visible result, ticket/requirement, inputs, outputs, source versions, units/coordinates if applicable, side effects, run command and acceptance evidence. Identify who owns each file when work is parallel. For a one-off, keep this brief; for a production utility, use the template.

### 2. Search and choose deliberately

Search the existing tool directory, contracts and lesson ledger. Choose one: reuse unchanged; extend a compatible helper; replace a defective implementation with a migration; or create a new script for a genuinely different responsibility. Record the reason. Do not make nearly identical property-specific scripts when a validated parameterized helper will work.

### 3. Separate preparation from application

Prefer explicit inputs and output locations. A script that can change active/shared state should prepare a reviewable candidate by default and require an explicit application mode. Read-only reports need no artificial approval ceremony. Where output publication is itself requested, use validated, reversible publication within that scope.

Preserve raw input bytes and existing user edits. Bind derived artifacts to relevant source/snapshot hashes or semantic fingerprints. Avoid invalidating unrelated outputs for camera-only or documentation-only changes. Treat untracked/dirty target files as work to preserve, not disposable generated data.

### 4. Make execution predictable

- Validate required fields, identifiers, ranges, units and path containment before writes. Preserve nulls and leading zeroes.
- Use bounded requests, timeouts, retry limits and caches for network sources. Do not query agency services on every display refresh.
- Make equivalent inputs produce equivalent results where possible; record random seeds and unavoidable nondeterminism.
- Handle interrupted or concurrent publication: immutable candidate outputs, guarded atomic pointer replacement, conflict detection and recoverable prior versions as appropriate.
- Return actionable errors and nonzero exit status on failure. Never label a partial run complete or silently substitute fabricated data.
- Keep credentials, private records and restricted media out of committed outputs and logs. Inspect the staged diff and ignore rules before committing.

### 5. Verify the user's result

Check representative actual data, not only fixtures. Exercise meaningful missing/stale/ambiguous inputs and replay/preservation behavior when relevant. Inspect the rendered page, exported file, scene or API that the user receives. A valid mesh is not proof of visual quality; a matching identifier is not proof of current physical geometry; a passing test is not proof of a whole ticket.

Use an independent reviewer for substantial production acceptance. Assign a different person or agent from the implementer; roles alone do not create independence. Small reversible edits do not require serial management approvals. Coordinate independent acceptance with the project�s agreed batch cadence where applicable; do not add a new serial approval meeting for every script. Necessary local checks and source/geometry promotion gates still apply before the affected state is used.

### 6. Publish and consolidate

Update the affected contract, usage instructions, evidence and ticket together. Distinguish implemented, verified, accepted and released. State whether the work is local, committed, pushed, active in the application or still a proposal. Preserve an explicit list of unfinished requirements.

At the project's agreed batch boundary, review completed tickets together for conflicting changes, stale dependencies, source rights, actual output quality and scope drift. Continue independent ready work while another task awaits a missing source or review.

## Ownership without extra bureaucracy

The implementer owns the result and script contract. The analyst owns source interpretation. The independent reviewer tests the claims. The PM tracks dependencies and evidence. The Director resolves delivery conflicts and acceptance findings. The VP/sponsor handles strategic tradeoffs rather than approving every script. Human authorization remains necessary where the task or governing rules require it; do not invent additional approval steps.

## Adoption in another project

Copy this protocol and the two templates, then create a short project profile defining scope, authoritative sources, runtime commands, sensitive boundaries, review cadence and release conditions. Seed its lesson ledger from that project's observed evidence. Replace College Park-specific links and do not copy its factual claims as facts about the new project. Installing this protocol in one repository does not configure other chats, global memory or scheduled agents.
