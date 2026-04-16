# Chapter 5 SWE Draft for RigLab-AI

## 5.1 Final Prototype
### The Exact Narrative Text
The Software Engineering component of the RigLab-AI final prototype constitutes the real-time decision-support backbone of the multidisciplinary system. Within the implemented architecture, the SWE subsystem is responsible for receiving live telemetry streams over the local area network, validating packet integrity and signal ranges, computing derived hydraulic indicators from the incoming sensor and gate-angle inputs, classifying operational state through the anomaly engine, persisting processed states to the database, and distributing those states to the observer dashboard through persistent WebSocket channels. In addition to real-time situational awareness, the SWE subsystem also provides autonomous incident documentation by generating asynchronous PDF incident snapshots when the operational state transitions into a critical condition. Accordingly, the SWE prototype should be presented not as a supporting utility, but as the central orchestration layer that transforms raw field telemetry into actionable, time-bounded operational intelligence while remaining prepared for future integration with the external IMX500 edge camera that will supply the gate-angle measurement stream.

For Figure 6, the multidisciplinary prototype figure should explicitly depict the SWE contribution as a bounded local stack containing Dockerized services, the FastAPI backend, the WebSocket ingest and broadcast server, the PostgreSQL/TimescaleDB persistence layer, the anomaly engine, and the PDF incident reporting module. The figure should show inbound telemetry entering the backend from the edge acquisition side, processed state updates flowing from the backend to the React dashboard, and a distinct path from anomaly detection to automatic incident report generation. The future IMX500 camera should appear as an upstream source of pre-calculated gate-angle telemetry rather than as part of the current SWE implementation. For Figure 7, the Venn diagram should place Software Engineering at the intersection of Petroleum Engineering and the hardware domain by labeling the SWE-PETE overlap with flow-deviation modeling, alarm thresholds, and incident interpretation logic, and labeling the SWE-hardware overlap with telemetry acquisition interfaces, LAN transport, synchronization handling, and edge-provided gate-angle integration.

### Explicit Evidence Directives
- Insert Figure 6 as a system architecture figure that highlights the SWE stack boundary and labels `FastAPI`, `WebSocket server`, `PostgreSQL/TimescaleDB`, `Anomaly Engine`, and `PDF Incident Reporter`.
- Insert Figure 7 as a Venn diagram with three circles: `Software Engineering`, `Petroleum Engineering`, and `Hardware/Embedded Systems`.
- Use a screenshot of the project structure or architecture diagram showing the backend modules and the local stack layout.
- If available, include a diagram callout showing the path `Telemetry -> Validation -> Classification -> Dashboard -> Incident PDF`.

### Rubric Check
This section meets the Exemplary tier by defining the SWE subsystem as a technically central, deeply integrated part of the multidisciplinary prototype and by clearly articulating subsystem boundaries, interfaces, and responsibilities.

## 5.1.1 Prototype Build
### The Exact Narrative Text
The RigLab-AI SWE prototype was built as a containerized, offline-first backend platform intended to execute entirely within a local area network. The implemented software stack deploys through Docker, allowing the backend services, database services, and dashboard environment to be launched in a controlled and reproducible manner without dependence on external cloud infrastructure. On initialization, the FastAPI application establishes the database connection pool, prepares the telemetry storage schema, loads the configurable operating constants required by the anomaly engine, and activates the WebSocket routes that support both telemetry ingestion and live dashboard broadcasting. This startup sequence creates a deterministic software environment in which operational state processing begins immediately after service readiness is achieved.

From an SWE perspective, the prototype build demonstrates that the backend has been engineered as a deployable operational service rather than as a laboratory-only codebase. The WebSocket ingest endpoint accepts continuous telemetry packets across the LAN, the processing layer transforms those packets into validated and classified state objects, and the broadcast endpoint distributes the processed stream to live dashboard clients with minimal overhead. Because the full application stack runs locally and all core services are self-hosted, the prototype supports offline execution at the network level while preserving real-time observability, persistence, and reporting. This build strategy also reduces configuration drift across environments, since the same service definitions and initialization logic can be reproduced consistently on any standard workstation configured for the project.

### Explicit Evidence Directives
- Insert a screenshot of Docker containers showing the backend, frontend, and database services running concurrently.
- Insert a screenshot of the terminal output during backend startup showing service initialization and server readiness.
- Insert a screenshot or browser capture of `GET /api/v1/health` returning a healthy system status.
- Insert a dashboard screenshot that shows an active live connection, confirming the LAN WebSocket path is operational.
- If space allows, include a small code figure citing the startup lifecycle and WebSocket route registration from `backend/main.py` and `backend/routers/websocket.py`.

### Rubric Check
This section meets the Exemplary tier by demonstrating a complete, technically deployable software build with clear operational behavior, local-network execution, and evidence-backed service integration.

## 5.1.2 Safety
### The Exact Narrative Text
Software safety in RigLab-AI is implemented through defensive validation, state-transition discipline, and communication continuity safeguards. At the ingest boundary, each telemetry packet is evaluated for the presence and admissible range of critical fields such as pressure, flow, gate angle, and confidence values before it is permitted to enter the operational decision path. Packets that violate structural or physical constraints are not allowed to propagate as valid operational states; instead, the processing layer converts them into explicit sensor-fault conditions so that the dashboard and downstream logic can distinguish instrumentation degradation from genuine hydraulic anomalies. This approach prevents corrupted or incomplete telemetry from contaminating the decision-support state machine.

The anomaly engine provides a second software safety barrier by enforcing temporal smoothing through a sustained-deviation window before issuing a critical state transition. Rather than reacting to a single transient excursion, the classifier requires consecutive qualifying deviations before changing the system from `NORMAL` to `KICK_RISK` or `LOSS_RISK`. This design materially reduces the risk of false-positive alarms that could otherwise provoke unnecessary operational responses. On the presentation side, dashboard continuity is protected through automatic reconnect and connection recovery logic in the live WebSocket client. If the live stream is interrupted, the client repeatedly attempts to re-establish the session so that operator awareness is restored promptly without manual reconfiguration. Taken together, these measures show that the SWE implementation treats safety not only as anomaly detection accuracy, but also as integrity preservation, false-alarm suppression, and resilient operator visibility.

### Explicit Evidence Directives
- Insert a code screenshot from `backend/processing.py` showing required-field validation, range checks, and sensor-fault handling.
- Insert a code screenshot from `backend/anomaly_engine.py` showing the consecutive-window logic that smooths state transitions.
- Insert a screenshot of the dashboard connection indicator showing live connection status and recovery behavior.
- Insert a short terminal excerpt showing how malformed telemetry is rejected or converted into a fault state instead of being processed as a normal operating event.
- If possible, add a small annotated diagram of the safety path: `Invalid packet -> Fault classification` and `Transient spike -> Windowed evaluation -> Alarm only after sustained breach`.

### Rubric Check
This section meets the Exemplary tier by connecting concrete defensive software mechanisms directly to operational safety outcomes and by showing how the backend prevents both corrupted inputs and unnecessary critical alarms.

## 5.1.3 Cost
### The Exact Narrative Text
The SWE implementation of RigLab-AI was intentionally constructed around open-source, locally deployable technologies in order to minimize lifecycle cost while preserving professional-grade backend capability. The software stack uses FastAPI for asynchronous API and WebSocket services, React for the observer interface, PostgreSQL with TimescaleDB for time-series persistence, and Docker for consistent service orchestration. This choice removes the need for proprietary enterprise middleware, recurring software licensing, or managed cloud processing services. As a result, the backend can execute on standard off-the-shelf workstation hardware without requiring specialized server infrastructure or vendor-specific deployment contracts.

Cost efficiency is further improved by the containerized deployment model. Docker reduces environment setup time, simplifies dependency control, and minimizes the engineering overhead associated with reproducing the platform across development, demonstration, and validation machines. The decision to keep computation and storage within the local workstation environment also eliminates ongoing cloud hosting charges, bandwidth-related operating costs, and the risk of cost growth caused by continuous remote telemetry processing. Therefore, the SWE contribution does not merely reduce software procurement cost; it also reduces integration cost, deployment effort, maintenance friction, and operational overhead across the entire backend lifecycle.

### Explicit Evidence Directives
- Insert a technology stack table listing `FastAPI`, `React`, `PostgreSQL/TimescaleDB`, and `Docker`, along with each tool's SWE role.
- Insert a screenshot or excerpt of `docker-compose.yml` to demonstrate consolidated local orchestration.
- Insert a workstation screenshot showing the full local stack running on a standard desktop machine.
- If appropriate, include a small comparison table contrasting the implemented local open-source stack with a hypothetical cloud-hosted or proprietary middleware alternative.

### Rubric Check
This section meets the Exemplary tier by translating technology selection into concrete engineering and operational cost savings rather than presenting cost only as a licensing discussion.

## 5.2 Verification Test Description
### The Exact Narrative Text
Two verification tests were used to evaluate whether the implemented SWE backend satisfied the principal software performance constraints of the RigLab-AI prototype. The first test focused on latency and throughput by driving a sustained controlled telemetry workload through the full ingest-to-process path and measuring the resulting processing delay and alarm-transition timing. In this test, the benchmark executed 100 telemetry packets through the operational processing pipeline and measured the elapsed time between packet receipt and processed-state completion using a dedicated benchmark script. The benchmark results showed an average ingest-to-process latency of 0.096979 ms and a maximum observed ingest-to-process latency of 4.623652 ms, both of which are orders of magnitude below the required 1.0 s dashboard-update constraint for the software path. The same benchmark also verified the anomaly engine timing logic under the configured sampling rate of 1 Hz and anomaly window of 2 samples, yielding a mathematically bounded alarm-transition latency of 2.0000 s for both kick and loss detection. Under these measured conditions, the backend therefore satisfied the required timing envelope for real-time processing and alarm state transition.

The second verification test evaluated automated incident reporting by inducing a controlled transition from `NORMAL` to `KICK_RISK` through the live telemetry stream and observing the anomaly engine's asynchronous reporting path. Once the classifier confirmed the sustained deviation window and issued the critical-state transition, the backend automatically invoked the incident snapshot generation routine and wrote the corresponding PDF artifact to the designated report output directory. The generated report contained the incident classification, timestamp, and synchronized processed-state fields required for event documentation. The successful creation of these artifacts immediately after the anomaly transition demonstrated that the reporting path operates autonomously rather than relying on a manual dashboard command. When interpreted together, the verification results show that the implemented SWE backend met the software-side timing constraints under the measured benchmark workload: processing latency remained comfortably under the dashboard limit, alarm latency was mathematically bounded by the configured window and sampling rate, and autonomous PDF incident generation confirmed end-to-end backend readiness for critical-event capture.

### Explicit Evidence Directives
- Insert a screenshot of the terminal output from `python scripts/benchmark.py` showing payload count, average latency, maximum latency, and the `PASS` status lines.
- Insert a screenshot of the generated incident PDF file in the output directory and another screenshot of the opened PDF showing the incident classification and timestamp.
- Insert a figure or small diagram showing the verification path `Telemetry injection -> Processing -> Anomaly transition -> Automatic PDF generation`.
- Insert, if available, a brief table summarizing the measured results:
  `Average ingest-to-process latency = 0.096979 ms`,
  `Maximum ingest-to-process latency = 4.623652 ms`,
  `Kick alarm latency = 2.0000 s`,
  `Loss alarm latency = 2.0000 s`.
- Cite the benchmark configuration from `backend/config.py` and the benchmark logic from `scripts/benchmark.py` in the figure caption or surrounding text.

### Rubric Check
This section meets the Exemplary tier by presenting quantitative verification results, interpreting their engineering significance, and linking the measured evidence directly to the software performance constraints claimed by the prototype.
