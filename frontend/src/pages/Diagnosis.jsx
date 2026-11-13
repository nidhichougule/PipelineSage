import React from 'react';
import { MOCK_ACTIVE_DIAGNOSIS } from '../data/mockData';

export default function Diagnosis({ onBack }) {
  const diagnosis = MOCK_ACTIVE_DIAGNOSIS;

  return (
    <div className="diagnosis-container">
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
        {onBack ? (
          <button className="btn-action" onClick={onBack}>
            ← Back to Workflow Runs
          </button>
        ) : <div />}
        <span style={{ fontSize: '0.75rem', color: 'var(--text-muted)' }}>
          Demo Diagnosis Preview
        </span>
      </div>

      <div className="alert-banner">
        <div>
          <div className="alert-title">
            Suspected Root Cause: {diagnosis.topSuspectedCause}
          </div>
          <div className="alert-subtitle">
            Failure Category: <strong>{diagnosis.detectedCategory}</strong> | Failing Stage: <strong>{diagnosis.failingStep}</strong>
          </div>
        </div>
        <div style={{ textAlign: 'right' }}>
          <span style={{ fontSize: '0.8rem', color: 'var(--text-secondary)' }}>
            Diagnosis Confidence
          </span>
          <div style={{ fontSize: '1.25rem', fontWeight: 700, color: 'var(--accent-purple)' }}>
            {(diagnosis.confidenceScore * 100).toFixed(0)}%
          </div>
        </div>
      </div>

      <div className="diagnosis-grid">
        <div>
          <div className="panel">
            <div className="panel-header">
              <span className="panel-title">Extracted Error Traceback</span>
              <span style={{ fontFamily: 'var(--font-mono)', fontSize: '0.75rem', color: 'var(--text-muted)' }}>
                Job #{diagnosis.runId}
              </span>
            </div>
            <div style={{ padding: '16px' }}>
              <div className="log-viewer">
                {diagnosis.rawLogExcerpt.map((line, idx) => (
                  <span
                    key={idx}
                    className={`log-line ${line.includes('ERROR') || line.includes('ModuleNotFoundError') ? 'error' : ''}`}
                  >
                    {line}
                  </span>
                ))}
              </div>
            </div>
          </div>

          <div className="panel">
            <div className="panel-header">
              <span className="panel-title">Recommended Recovery Actions</span>
            </div>
            <div style={{ padding: '16px' }}>
              <ol style={{ paddingLeft: '20px', fontSize: '0.85rem', color: 'var(--text-secondary)', display: 'flex', flexDirection: 'column', gap: '8px' }}>
                {diagnosis.recommendedActions.map((action, i) => (
                  <li key={i} style={{ color: 'var(--text-primary)' }}>
                    {action}
                  </li>
                ))}
              </ol>
            </div>
          </div>
        </div>

        <div>
          <div className="evidence-box">
            <div className="evidence-title">
              <svg width="18" height="18" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 8v4l3 3m6-3a9 9 0 11-18 0 9 9 0 0118 0z" />
              </svg>
              <span>Temporal Correlation Evidence</span>
            </div>

            <div className="evidence-item">
              <div className="evidence-label">Last Known Passing Commit</div>
              <div className="evidence-val">{diagnosis.temporalCorrelation.lastGreenCommit}</div>
            </div>

            <div className="evidence-item">
              <div className="evidence-label">Time Elapsed Since Green Build</div>
              <div className="evidence-val">{diagnosis.temporalCorrelation.temporalProximityMinutes} minutes</div>
            </div>

            <div className="evidence-item">
              <div className="evidence-label">Changed Files in Commit ({diagnosis.commitHash})</div>
              <div className="evidence-val" style={{ display: 'flex', flexDirection: 'column', gap: '4px', marginTop: '6px' }}>
                {diagnosis.temporalCorrelation.changedFiles.map((file, idx) => (
                  <span key={idx} style={{ color: 'var(--accent-blue)', fontSize: '0.75rem' }}>
                    • {file}
                  </span>
                ))}
              </div>
            </div>

            <div className="evidence-item">
              <div className="evidence-label">Historical Recurrence</div>
              <div className="evidence-val">
                Seen {diagnosis.temporalCorrelation.recurrenceCount} times across prior builds
              </div>
            </div>

            <div style={{ marginTop: '16px' }}>
              <div className="evidence-label">Correlation Confidence</div>
              <div className="confidence-meter">
                <div className="meter-bar">
                  <div
                    className="meter-fill"
                    style={{ width: `${diagnosis.confidenceScore * 100}%` }}
                  ></div>
                </div>
                <span style={{ fontSize: '0.8rem', fontFamily: 'var(--font-mono)' }}>
                  {diagnosis.confidenceScore * 100}%
                </span>
              </div>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}
