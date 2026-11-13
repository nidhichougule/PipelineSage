import React from 'react';
import StatCard from '../components/StatCard';
import { MOCK_METRICS, MOCK_WORKFLOW_RUNS } from '../data/mockData';

export default function Dashboard({ onSelectRun }) {
  return (
    <div>
      <div className="stats-grid">
        <StatCard
          title="Total Workflow Runs"
          value={MOCK_METRICS.totalRuns}
          subtext="Tracked across all branches"
        />
        <StatCard
          title="Pipeline Failure Rate"
          value={MOCK_METRICS.failureRate}
          subtext="Last 30 days of builds"
        />
        <StatCard
          title="Diagnosed Failures"
          value={MOCK_METRICS.diagnosedFailures}
          subtext="Root-cause signatures matched"
        />
        <StatCard
          title="Avg Triage Latency"
          value={MOCK_METRICS.avgTriageTime}
          subtext="Log extraction & correlation"
        />
      </div>

      <div className="panel">
        <div className="panel-header">
          <span className="panel-title">Recent Workflow Executions</span>
          <span style={{ fontSize: '0.75rem', color: 'var(--text-muted)' }}>
            Demo Data Preview
          </span>
        </div>
        <div className="table-wrapper">
          <table>
            <thead>
              <tr>
                <th>Run ID</th>
                <th>Workflow</th>
                <th>Branch</th>
                <th>Commit</th>
                <th>Status</th>
                <th>Duration</th>
                <th>Failure Category</th>
                <th>Actions</th>
              </tr>
            </thead>
            <tbody>
              {MOCK_WORKFLOW_RUNS.map((run) => (
                <tr key={run.id}>
                  <td style={{ fontFamily: 'var(--font-mono)' }}>#{run.id}</td>
                  <td>{run.workflow}</td>
                  <td style={{ fontFamily: 'var(--font-mono)', color: 'var(--text-secondary)' }}>
                    {run.branch}
                  </td>
                  <td style={{ fontFamily: 'var(--font-mono)' }}>{run.commit}</td>
                  <td>
                    <span className={`status-badge ${run.status}`}>
                      {run.status}
                    </span>
                  </td>
                  <td>{run.duration}</td>
                  <td>
                    {run.category === 'None' ? (
                      <span style={{ color: 'var(--text-muted)' }}>—</span>
                    ) : (
                      <span className="status-badge warning">{run.category}</span>
                    )}
                  </td>
                  <td>
                    {run.status === 'failure' ? (
                      <button
                        className="btn-action"
                        onClick={() => onSelectRun(run.id)}
                      >
                        Inspect Diagnosis
                      </button>
                    ) : (
                      <button className="btn-action" disabled style={{ opacity: 0.5 }}>
                        Healthy
                      </button>
                    )}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </div>
    </div>
  );
}
