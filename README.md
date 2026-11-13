# PipelineSage — Intelligent CI/CD Failure Diagnosis

> An explainable, temporal root-cause localization and developer-observability platform for GitHub Actions CI/CD workflows.

---

## 1. Project Overview & Motivation

Continuous Integration and Continuous Delivery (CI/CD) pipelines fail frequently in modern agile teams due to dependency mismatches, configuration shifts, flaky tests, code regressions, and infrastructure hiccups. When a build fails on GitHub Actions, developers often encounter:
- Massive, verbose, unstructured log files spanning thousands of lines.
- Cryptic exit codes without context regarding recent repository edits.
- Repetitive, manual triaging effort to determine whether an error was introduced by the latest commit, a third-party package upgrade, or a flaky test runner.

**PipelineSage** is an intelligent developer tool designed to bridge this gap. Instead of merely pattern-matching error strings inside raw logs, PipelineSage investigates the **temporal and historical context** of the repository:
1. Connecting to GitHub repositories via the GitHub REST API.
2. Collecting failed job metadata and raw logs.
3. Parsing logs to extract structured error signatures, stack traces, and pipeline execution stages.
4. Classifying failures into structured taxonomy categories (Dependency, Syntax, Test, Build, Environment, Network, Configuration).
5. **Correlating current failures with historical workflow trends, commit metadata, changed files, and test history.**
6. Ranking suspected root causes with explainable, human-verifiable evidence.
7. Presenting actionable recovery recommendations through a React-based observability dashboard.

---

## 2. Research Question & Proposed Contribution

### Main Research Question
> *Can historical workflow patterns, commit changes, and test outcomes improve root-cause localization accuracy compared with traditional log-based failure classification alone?*

### Proposed Contribution
- **Explainable Temporal Failure-Correlation Engine**: Rather than treating each build failure in isolation or relying on a black-box model, PipelineSage introduces an explainable ranking engine. It systematically scores suspected causes using:
  - Historical failure signatures and recurrence patterns.
  - Commit timestamps and commit authorship.
  - Changed file extensions and semantic relevance to the failing pipeline stage.
  - Recency and frequency of prior green/red builds across branches.
  - Test outcomes and failure co-occurrence.
- **Evidence-Backed Ranking**: Diagnoses are output as *suspected causes with transparent scoring breakdowns and supporting evidence* (e.g., related commits, past matching runs) rather than unverified assertions.

---

## 3. Technology Stack

| Layer | Technology | Purpose |
|---|---|---|
| **Backend API** | Python 3.11 + FastAPI | Async REST API, orchestration, diagnosis engine |
| **Data Processing & ML** | pandas, scikit-learn | Log feature extraction, similarity scoring, baseline classifiers |
| **Database & ORM** | PostgreSQL + SQLAlchemy 2.0 | Persistent relational storage for repositories, runs, logs, and diagnoses |
| **Database Migrations** | Alembic | Trackable database schema versioning |
| **Frontend UI** | React 18 + Vite + Tailwind CSS | Fast, clean developer observability dashboard |
| **External Integration**| GitHub REST API | Workflow runs, jobs, logs, commits, pull requests, file diffs |
| **Testing** | pytest, pytest-asyncio, Vitest | Unit, integration, and regression testing |
| **Containerization** | Docker, Docker Compose | Reproducible multi-container local stack |
| **Observability** | Prometheus | API latency, log triage throughput, and diagnosis metrics |

---

## 4. System Architecture

```mermaid
flowchart TD
    subgraph GitHub["GitHub Platform"]
        GH_REPO["Target Repository"]
        GH_ACTIONS["GitHub Actions Workflows"]
        GH_API["GitHub REST API"]
    end

    subgraph Backend["PipelineSage Backend (FastAPI)"]
        API_ROUTER["API Routes (/runs, /diagnose, /metrics)"]
        GH_SERVICE["GitHub Service (Async Client)"]
        LOG_PARSER["Log Parser & Stack Trace Extractor"]
        CLASSIFIER["Failure Classifier (Rule-Based & TF-IDF)"]
        TEMPORAL_ENGINE["Temporal Correlation Engine"]
        DB_LAYER["SQLAlchemy ORM & Repository Pattern"]
    end

    subgraph Storage["Persistence & Telemetry"]
        PG_DB[("PostgreSQL Database")]
        PROM_SRV["Prometheus Metrics Server"]
    end

    subgraph Frontend["PipelineSage Dashboard (React + Vite)"]
        UI_DASH["Dashboard & Overview"]
        UI_RUNS["Workflow History & Filters"]
        UI_DIAG["Ranked Diagnosis & Evidence Explorer"]
        UI_METRICS["System Health & Evaluation Metrics"]
    end

    GH_ACTIONS -->|Runs & Logs| GH_API
    GH_API -->|Webhooks / Polling| GH_SERVICE
    GH_SERVICE --> API_ROUTER
    API_ROUTER --> LOG_PARSER
    LOG_PARSER --> CLASSIFIER
    CLASSIFIER --> TEMPORAL_ENGINE
    TEMPORAL_ENGINE --> DB_LAYER
    DB_LAYER <--> PG_DB
    API_ROUTER --> PROM_SRV
    Frontend <-->|REST API / JSON| API_ROUTER
```

---

## 5. Development Roadmap (16 Phases)

- **Phase 0 — Project Planning & Environment Inspection** *(Current)*
- **Phase 1 — Backend Foundation (FastAPI)**
- **Phase 2 — Frontend Foundation (React + Vite)**
- **Phase 3 — GitHub Actions Demo Repository (Controlled Failure Scenarios)**
- **Phase 4 — GitHub API Integration Service**
- **Phase 5 — Intelligent Log Parser & Error Extraction**
- **Phase 6 — Failure Classifier (Rule-Based & TF-IDF Baseline)**
- **Phase 7 — Temporal Failure-Correlation Engine (Core Research Component)**
- **Phase 8 — PostgreSQL Database & Alembic Migrations**
- **Phase 9 — End-to-End Frontend & Backend Integration**
- **Phase 10 — Testing, Evaluation Dataset & Empirical Benchmarking**
- **Phase 11 — Containerization with Docker & Docker Compose**
- **Phase 12 — GitHub Actions CI for PipelineSage**
- **Phase 13 — Prometheus Telemetry & Metrics Instrumentation**
- **Phase 14 — Kubernetes Manifests & Local Cluster Deployment (Kind/Minikube)**
- **Phase 15 — Final Documentation, Artifacts & Interview Portfolio Preparation**

---

## 6. Local Setup & Prerequisites

### System Requirements
- **OS**: Windows 10/11 (PowerShell)
- **Python**: 3.11.x
- **Node.js**: v20+ / v22+ with npm
- **Git**: 2.40+
- **Docker**: (Optional during initial local development; required for Phase 11+)

### Environment Variables
PipelineSage uses a `.env` file for configuration. A template is provided in `.env.example`:
```env
APP_NAME=PipelineSage
APP_ENV=development
API_PORT=8000
GITHUB_PERSONAL_ACCESS_TOKEN=your_github_pat_here
DATABASE_URL=postgresql+psycopg2://postgres:postgres@localhost:5432/pipelinesage
```

> **Security Note**: Never commit actual GitHub tokens or database passwords to version control. Keep `.env` included in `.gitignore` at all times.

---

## 7. License & Academic Integrity
Developed as an engineering research project. All empirical evaluations, baseline comparisons, and accuracy numbers reported within this repository reflect reproducible experimental outcomes on documented datasets.
