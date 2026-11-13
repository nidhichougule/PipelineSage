# PipelineSage — Project Plan & Engineering Roadmap

---

## 1. Environment Inspection & Hardware Profile

An initial environment audit was conducted on the development machine.

| Check | Specification / Result | Status | Notes |
|---|---|---|---|
| **Operating System** | Windows 10/11 Home/Pro (PowerShell 5.1/7+) | Verified | Use Windows PowerShell commands exclusively |
| **CPU & Architecture** | Intel Core i5-1235U (10 Cores: 2P + 8E) | Verified | Efficient multi-threading, moderate single-core burst |
| **Memory (RAM)** | 8.00 GB Physical RAM | Constraint | Must run lean services; avoid simultaneous memory hogs |
| **Primary Storage (C:)** | 117.75 GB Available Free Space | Verified | Sufficient for Python venv, node_modules, and Postgres |
| **Secondary Storage (D:)** | 185.17 GB Available Free Space | Verified | Available for backups, container images, or datasets |
| **Python** | Python 3.11.9 (64-bit) | Verified | Fully compatible with FastAPI, SQLAlchemy 2.0, pandas |
| **Node.js** | v22.15.0 | Verified | Compatible with Vite 5/6, React 18/19 |
| **npm** | 10.9.2 | Verified | Stable package manager |
| **Git** | git version 2.49.0.windows.1 | Verified | Modern Git client |
| **Docker Engine / CLI** | Not found in PATH / Inactive | Deferred | Expected for Phase 0; deferred to Phase 11 |

### RAM & Resource Management Strategy
With 8 GB RAM on the host machine:
1. **Phased execution**: Develop backend (FastAPI) and frontend (Vite) locally with lightweight virtual environments (`.venv` and `node_modules`) before introducing containers.
2. **PostgreSQL**: Run local SQLite during early logic verification (Phase 1-7) or lightweight local PostgreSQL service without excessive connection pool sizes.
3. **Docker Compose (Phase 11)**: Limit memory allocation per container in `docker-compose.yml` (`mem_limit: 512m` for backend, `256m` for frontend, `512m` for PostgreSQL).
4. **Kubernetes (Phase 14)**: Use single-node `kind` or `k3s`/`Minikube` with a strict memory limit (`--memory=2048m`), keeping cluster operations strictly isolated to Phase 14 testing.

---

## 2. Research Focus & Architectural Concept

### The Problem
Traditional CI/CD log triage relies either on:
1. **Naive regex / keyword matching**: Misses semantic context, fails when error formats change, cannot explain root causes across commits.
2. **Generic LLM summarization**: Prone to hallucinating solutions, costly, and lacks access to the temporal history of the code repository (e.g., "did this test pass 2 commits ago before file X was changed?").

### PipelineSage Temporal Correlation Solution
PipelineSage constructs a multi-signal diagnostic graph for any failing run:
- **Signal 1: Log Error Signature ($S_{log}$)**: Normalized exception class, message, stack trace top-frame, failing step.
- **Signal 2: Temporal Proximity ($S_{time}$)**: Time delta between the last successful workflow run and the failing commit.
- **Signal 3: File-Stage Semantic Overlap ($S_{diff}$)**: Jaccard & heuristic similarity between modified file paths in the commit diff and the failing step dependencies (e.g., changes to `requirements.txt` preceding a `ModuleNotFoundError` during setup).
- **Signal 4: Historical Recurrence ($S_{hist}$)**: Prior runs sharing similar error signatures and their confirmed remedies.
- **Signal 5: Test Flakiness Index ($S_{test}$)**: Transition frequency (pass $\rightarrow$ fail $\rightarrow$ pass without code changes) of individual test cases.

The output is a ranked set of **Suspected Root Causes** accompanied by concrete historical evidence.

---

## 3. Phase-by-Phase Roadmap

### Phase 0: Project Planning & Environment Inspection *(Current Phase)*
- [x] Inspect OS, Python, Node, npm, Git, disk, and RAM.
- [x] Establish repository structure and `.gitignore`.
- [x] Author comprehensive `README.md` and `PROJECT_PLAN.md`.
- [ ] User review and sign-off.

### Phase 1: Backend Foundation (FastAPI) [Completed]
- [x] Set up modular FastAPI backend (app/main.py, core/config.py, models/schemas.py, routes/).
- [x] Implement GET / and GET /health endpoints with structured exception handlers.
- [x] Create backend/.venv virtual environment and verify all pytest tests pass.

### Phase 2: Frontend Foundation (React + Vite) [Completed]
- [x] Scaffold responsive React 18 + Vite developer dashboard in pure JavaScript.
- [x] Implement dark-mode DevOps observability UI with Sidebar, Header, and StatCard components.
- [x] Implement Dashboard, WorkflowRuns, Diagnosis, and Settings pages with clearly labeled mock data.
- [x] Verify production build (vite build) and local development server.

### Phase 3: GitHub Actions Demo Repository
- **Goal**: Create a controlled, reproducible testbed repository with intentional failure modes.
- **Controlled Failure Scenarios**:
  1. *Success Run*: Clean build and passing pytest suite.
  2. *Dependency Failure*: Incompatible/missing requirement in `requirements.txt` (`ModuleNotFoundError`).
  3. *Unit Test Failure*: Intentionally failing assertion in a test case (`AssertionError`).
  4. *Syntax Error*: Invalid Python syntax in a source file (`SyntaxError`).
  5. *Configuration Error*: Invalid GitHub Actions YAML or bad environment variable.
- **Verification**: Document commit hashes, workflow run IDs, and verified causes.

### Phase 4: GitHub API Integration Service
- **Goal**: Build an asynchronous GitHub REST API client capable of fetching workflow metadata and logs.
- **Key Modules**:
  - `backend/app/services/github_service.py`: Octokit-equivalent client with rate-limit handling, pagination, and log decompression.
  - Endpoints: `GET /api/v1/github/runs`, `GET /api/v1/github/runs/{run_id}`, `GET /api/v1/github/runs/{run_id}/logs`.
- **Verification**: Fetch real workflow runs from the demo repository and verify parsed JSON output.

### Phase 5: Intelligent Log Parser & Error Extraction
- **Goal**: Transform raw, multi-thousand-line CI log streams into structured diagnostic records.
- **Key Modules**:
  - `backend/app/analyzers/log_parser.py`: Multi-stage regex and parser isolating failed step, ANSI stripping, stack trace identification, and error frame extraction.
- **Verification**: Unit tests on simulated and real GitHub Actions logs covering 7 major error categories.

### Phase 6: Failure Classifier (Rule-Based & TF-IDF Baseline)
- **Goal**: Categorize extracted errors into a taxonomy.
- **Categories**: Dependency, Syntax, Test, Build, Environment, Network, Configuration, Unknown.
- **Key Modules**:
  - `backend/app/analyzers/failure_classifier.py`: Rule-based pattern matching engine + confidence heuristic.
  - Baseline comparison script with TF-IDF + Logistic Regression / Naive Bayes.
- **Verification**: Precision and recall metrics on a labeled log test set.

### Phase 7: Temporal Failure-Correlation Engine (Core Contribution)
- **Goal**: Implement the correlation algorithm that leverages historical context.
- **Key Modules**:
  - `backend/app/analyzers/temporal_engine.py`: Multi-factor correlation scoring engine.
  - Explanations generator producing human-readable rationale and evidence links.
- **Verification**: Synthetic historical runs evaluated; explainable breakdown verified.

### Phase 8: PostgreSQL Database & Alembic Migrations
- **Goal**: Persist repositories, workflow runs, jobs, commit metadata, and diagnosis outputs.
- **Key Modules**:
  - `backend/app/models/`: SQLAlchemy declarative models (`Repository`, `WorkflowRun`, `Job`, `Commit`, `Diagnosis`).
  - `backend/alembic/`: Migration scripts and revision history.
- **Verification**: Run migrations up/down; execute CRUD tests with SQLAlchemy session fixtures.

### Phase 9: End-to-End Frontend & Backend Integration
- **Goal**: Wire the React dashboard directly to FastAPI endpoints backed by PostgreSQL.
- **Verification**: Live workflow triage flow tested from browser UI through to database persistence.

### Phase 10: Testing, Evaluation & Empirical Benchmarking
- **Goal**: Measure and scientifically document diagnostic performance.
- **Metrics**:
  - Top-1 Accuracy: Is the primary suspect cause the actual root cause?
  - Top-3 Accuracy: Is the actual root cause within the top-3 suspects?
  - Mean Reciprocal Rank (MRR): $\frac{1}{|Q|}\sum_{i=1}^{|Q|}\frac{1}{\text{rank}_i}$
  - False-Positive Rate & Median Latency.
- **Verification**: Comparison report generated comparing *Log-Only Baseline* vs. *PipelineSage Temporal Engine*.

### Phase 11: Containerization with Docker & Docker Compose
- **Goal**: Package backend, frontend, and PostgreSQL into production-grade multi-stage containers.
- **Deliverables**: `backend/Dockerfile`, `frontend/Dockerfile`, `docker-compose.yml`.

### Phase 12: GitHub Actions CI for PipelineSage
- **Goal**: Automate testing, linting, and Docker building for PipelineSage repository.

### Phase 13: Prometheus Telemetry & Monitoring
- **Goal**: Export application metrics (HTTP latency, triage throughput, error distributions).

### Phase 14: Kubernetes Deployment (Kind / Minikube)
- **Goal**: Create production-style Kubernetes manifests (Deployments, Services, ConfigMaps, Secrets).

### Phase 15: Final Documentation & Portfolio Presentation
- **Goal**: Clean, interview-ready README, architecture diagrams, benchmark graphs, and demo walkthrough.

---

## 4. Immediate Next Step

With Phase 0 documentation completed, Phase 1 (Backend Foundation) will initialize the Python virtual environment, install FastAPI and uvicorn, and create the baseline modular directory structure.
