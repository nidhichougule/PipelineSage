import React, { useState } from 'react';
import { MOCK_WORKFLOW_RUNS } from '../data/mockData';

export default function WorkflowRuns({ onSelectRun }) {
  const [filter, setFilter] = useState('all');

  const filteredRuns = MOCK_WORKFLOW_RUNS.filter((run) => {
    if (filter === 'all') return true;
    return run.status === filter;
  });

  return (
    <div className="panel">
      <div className="panel-header">
        <div>
          <span className="panel-title">Workflow Execution History</span>
          <span style={{ fontSize: '0.75rem', color: 'var(--text-muted)', marginLeft: '12px' }}>
            Demo Data Preview
          </span>
        </div>
        <div style={{ display: 'flex', gap: '8px' }}>
          <button
            className={`btn-action ${filter === 'all' ? 'active' : ''}`}
            onClick={() => setFilter('all')}
          >
            All Runs
          </button>
          <button
            className={`btn-action ${filter === 'failure' ? 'active' : ''}`}
            onClick={() => setFilter('failure')}
          >
            Failures Only
          </button>
          <button
            className={`btn-action ${filter === 'success' ? 'active' : ''}`}
            onClick={() => setFilter('success')}
          >
            Successes Only
          </button>
        </div>
      </div>
      <div className="table-wrapper">
        <table>
          <thead>
            <tr>
              <th>Run ID</th>
              <th>Workflow Name</th>
              <th>Branch</th>
              <th>Commit</th>
              <th>Author</th>
              <th>Status</th>
              <th>Duration</th>
              <th>Execution Time</th>
              <th>Action</th>
            </tr>
          </thead>
          <tbody>
            {filteredRuns.map((run) => (
              <tr key={run.id}>
                <td style={{ fontFamily: 'var(--font-mono)' }}>#{run.id}</td>
                <td>{run.workflow}</td>
                <td style={{ fontFamily: 'var(--font-mono)' }}>{run.branch}</td>
                <td style={{ fontFamily: 'var(--font-mono)' }}>{run.commit}</td>
                <td>{run.author}</td>
                <td>
                  <span className={`status-badge ${run.status}`}>
                    {run.status}
                  </span>
                </td>
                <td>{run.duration}</td>
                <td style={{ color: 'var(--text-muted)' }}>{run.timestamp}</td>
                <td>
                  {run.status === 'failure' ? (
                    <button
                      className="btn-action"
                      onClick={() => onSelectRun(run.id)}
                    >
                      View Diagnosis
                    </button>
                  ) : (
                    <span style={{ color: 'var(--text-muted)', fontSize: '0.8rem' }}>Clean</span>
                  )}
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );
}
