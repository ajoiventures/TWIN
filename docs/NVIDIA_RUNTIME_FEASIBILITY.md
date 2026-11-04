# NVIDIA runtime feasibility — bounded assessment

Assessed October 28, 2026 for the runtime/small-trial work in #29/#30. This is a read-only host and primary-documentation assessment. No installation, model download, credential creation, API inference, remote deployment or paid compute occurred. No model benchmark or full-runtime acceptance is claimed.

## Decision

Continue the existing Windows OpenUSD editor, official-data pipeline and local planning workbench. The laptop is not a documented full Smart City 3.3 deployment host. Evaluate heavy vision/reconstruction/generation on a separately verified Linux host only if a bounded experiment demonstrates a product need. Smaller service graphs reduce scope, but do not establish laptop compatibility.

## Measured, declared and unknown

Read-only Windows CIM queries and `nvidia-smi --query-gpu=name,memory.total,driver_version --format=csv,noheader` produced:

| Item | Evidence | Interpretation |
|---|---|---|
| Machine | Measured: Acer Predator PHN16S-71 | Current workstation |
| OS | Measured: Windows 11 Home, version 10.0.26200, build 26200 | Does not match the blueprint's documented Ubuntu host |
| CPU | Measured: Intel Core Ultra 9 275HX, 24 cores / 24 logical processors | Numeric core count clears the listed 18-core floor; no throughput benchmark |
| Installed RAM | Measured: 33,752,997,888 bytes, approximately 31.44 GiB | Below documented 128 GB Smart City RAM requirement |
| GPU | Measured: NVIDIA GeForce RTX 5070 Ti Laptop GPU | Not one of the Smart City page's validated GPUs |
| VRAM | Measured: 12,227 MiB, approximately 11.94 GiB | Total, not free memory or model headroom |
| Driver | Measured: 577.13 Windows | Not the documented Linux driver/runtime combination |
| C: storage | Measured at assessment: 237,028,077,568 bytes used; 785,552,670,720 bytes free | Approximately 731.6 GiB free. Does not verify physical SSD type, deployment partition or a reserved model/cache budget |
| Omniverse | Project-declared current Kit 110.4 | Existing scene/editor use; not a VSS/NuRec compatibility result |
| Unchecked | WSL/Linux guest, Docker/Compose/Buildx, Container Toolkit, CUDA runtime, NGC entitlements, model licenses, remote hosts, network throughput | Unknown; no assumption of readiness |

RAM/VRAM are separate resources. CPU offload, shared-memory marketing figures or adding VRAM totals across GPUs must not be used to satisfy a documented per-device profile floor.

## Exact Smart City 3.3 requirements checked

The [Smart City prerequisite page](https://docs.nvidia.com/vss/vision-agent/agent-workflows/industry-specific-examples/smart-city-blueprint/prerequisites) identifies version 3.3.0 and lists x86-64, 18 CPU cores, 128 GB RAM, 1 TB SSD and 1 Gbps networking; Ubuntu 24.04; and validation on H100, L40S or RTX PRO 6000 Blackwell. Its Compose path specifies Linux driver 595.58.03, Docker 28.3.3 or later but below 29.5.0, Compose 2.39.1+, Buildx 0.23.0 or later but below 0.35.0, Container Toolkit 1.17.8+, and NGC CLI 4.10.0+. NGC access is required; the supplied video-analytics map UI also calls for a Google Maps key.

The laptop fails documented RAM/OS compatibility and has an unvalidated GPU profile. CPU count alone is insufficient. Do not upgrade the Windows driver merely to match a Linux version number; evaluate the entire supported host/image combination first. Existing local map functionality does not depend on the supplied Google map UI.

## Modular profiles and local versus remote

The [VSS 3.3 prerequisite/profile guide](https://docs.nvidia.com/vss/getting-started/prerequisites) separates base, LVS, alerts and search graphs, with shared/dedicated GPUs and remote LLM/VLM placements. Validated layouts vary by hardware and profile from one to four GPUs. Its experimental OTHER configuration is not validation of this laptop. Shared host prerequisites still apply; remote models do not remove NGC access or automatically remove local video-processing needs. A browser client may reach a separate deployment host on port 7777. Standard deployment requires an NGC Personal API Key; other model/harness credentials depend on selected services.

| Option | Assessment | Gate before execution |
|---|---|---|
| Existing laptop GIS/USD/API and offline event replay | Proceed using current project tools | Preserve semantic/source validation and measure actual resolution, latency and memory |
| Full Smart City stack on laptop | Do not treat as supported | Would require a different verified deployment environment, not just fewer containers |
| One modular VSS workflow on eligible remote Linux GPU host | Candidate, not provisioned | Select exact profile, image digest, GPU layout and workload; verify host prerequisites and cold start |
| Remote LLM/VLM with local laptop client | Architectural candidate | Verify endpoint/service graph compatibility, data rights, latency and costs; no endpoint is currently configured by this assessment |
| Standalone video/model component on laptop | Undetermined | Check that component's own exact requirements; a full-stack failure does not prove every standalone component impossible |

Do not copy the generic VSS hardware tabs into Smart City deployment claims without checking the selected workflow's narrower support. No WSL support or production operating status has been established here.

## NuRec small-trial assessment

The [NuRec hardware guide](https://docs.nvidia.com/nurec/basics/hardware.html) specifies Linux x86-64, CUDA 12.8 or newer and more than 24 GB GPU memory; it recommends more than 48 GB and does not support Linux aarch64. Listed Blackwell RTX PRO 6000D configurations require R580 or later. The [official NuRec skills installation reference](https://github.com/NVIDIA/nurec-skills/blob/main/skills/nre/references/install.md) additionally describes container/NGC setup and substantial per-clip storage. These requirements do not describe the current 12 GB Windows laptop as a training host.

A bounded remote reconstruction trial would use one authorized, calibrated clip with documented camera poses/intrinsics and required LiDAR/NCore inputs, reconstruct a small area, compare held-out views and geometry against GIS evidence, and record runtime/memory/output size. A reconstructed visual surface is not a substitute for parcel, survey or accessibility measurements. Product/tool paths such as Instant NuRec must be evaluated separately; this report does not transfer NRE requirements to every NuRec-branded component.

## Cosmos 3 small-trial assessment

Use an exact release, not the name Cosmos alone. The [Cosmos 3.0.0 NIM support matrix](https://docs.nvidia.com/nim/cosmos/3.0.0/support-matrix.html), marked updated July 8, 2026, lists its Generator nano profile with a minimum 79 GiB per-device floor. Its super profiles have higher or multi-device floors. The laptop does not meet that nano floor. This is a specific NIM configuration result, not a universal claim about all Cosmos models or community offload paths.

The [current Cosmos 3 model overview](https://docs.nvidia.com/cosmos/latest/cosmos3/model_matrix.html) describes Super/Nano/Edge families differently from that pinned NIM matrix. These documentation tracks must not be mixed to invent a compatible 12 GB deployment. Select the actual model artifact, precision, runtime/image and matching support matrix before estimating feasibility. Smaller visual-reasoning and generative profiles are different workloads; an Edge model label alone does not prove video-generation compatibility.

A bounded remote generation trial would use one rendered pilot view and explicit controls, preserve inputs/seed/model version, compare geometry/label consistency and held-out real references, and measure peak memory, time and failure rate. Generated output remains synthetic; it cannot establish current storefronts, street geometry or traffic behavior.

## What can proceed now without new infrastructure

1. Freeze a trial manifest: use case, input rights, maximum clip/frame extent, expected outputs, evaluation metric and stop rule.
2. Prepare safe local render/reference packets, semantic labels and a small manually reviewed benchmark set using existing tools. Keep historic, proposed and synthetic inputs labeled.
3. Test existing GIS/API/scene contracts and deterministic event replay. Record those results as local project tests, not NVIDIA model execution.
4. Produce remote-host specifications and cost inputs after an exact workflow/profile is selected; no provisioning or spending is authorized by this assessment.

## Adoption and acceptance gate

Before a model trial: pin image/model versions and licenses; identify a compatible available host; verify free RAM/VRAM/disk, runtime and credentials without exposing keys; agree data handling and spend limits; perform a cold-start smoke test. Run one component at a time before adding a multi-service graph.

Before adoption: attach actual inputs/output hashes, model/config versions, startup/inference timings, memory peaks, crash/OOM history, task accuracy and geometry/label consistency evidence. Compare with the simpler local baseline. Retain optional status if benefit is unmeasured or the source/calibration gate fails.

This feasibility document completes a bounded prerequisite comparison only. Full runtime deployment, NuRec reconstruction, Cosmos inference, operating-cost measurement and model-performance acceptance remain unexecuted work.
