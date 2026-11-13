import React from 'react';

export default function Settings() {
  return (
    <div className="panel" style={{ maxWidth: '720px' }}>
      <div className="panel-header">
        <span className="panel-title">Repository & Connector Settings</span>
      </div>
      <div style={{ padding: '24px', display: 'flex', flexDirection: 'column', gap: '20px' }}>
        <div>
          <label style={{ display: 'block', fontSize: '0.8rem', color: 'var(--text-secondary)', marginBottom: '6px' }}>
            Connected GitHub Repository
          </label>
          <input
            type="text"
            readOnly
            value="nidhichougule/PipelineSage"
            style={{
              width: '100%',
              padding: '10px 12px',
              backgroundColor: 'var(--bg-tertiary)',
              border: '1px solid var(--border-color)',
              color: 'var(--text-primary)',
              borderRadius: '6px',
              fontFamily: 'var(--font-mono)',
              fontSize: '0.85rem',
            }}
          />
        </div>

        <div>
          <label style={{ display: 'block', fontSize: '0.8rem', color: 'var(--text-secondary)', marginBottom: '6px' }}>
            FastAPI Backend Endpoint
          </label>
          <input
            type="text"
            readOnly
            value="http://127.0.0.1:8000"
            style={{
              width: '100%',
              padding: '10px 12px',
              backgroundColor: 'var(--bg-tertiary)',
              border: '1px solid var(--border-color)',
              color: 'var(--text-primary)',
              borderRadius: '6px',
              fontFamily: 'var(--font-mono)',
              fontSize: '0.85rem',
            }}
          />
          <span style={{ fontSize: '0.75rem', color: 'var(--text-muted)', marginTop: '4px', display: 'block' }}>
            Integration active in Phase 9. Mock data currently displayed for UI layout.
          </span>
        </div>

        <div>
          <label style={{ display: 'block', fontSize: '0.8rem', color: 'var(--text-secondary)', marginBottom: '6px' }}>
            GitHub REST API Authentication Status
          </label>
          <div style={{ display: 'flex', alignItems: 'center', gap: '8px', color: 'var(--accent-amber)', fontSize: '0.85rem' }}>
            <span style={{ width: '8px', height: '8px', borderRadius: '50%', backgroundColor: 'var(--accent-amber)' }}></span>
            <span>Pending GitHub Personal Access Token configuration (Scheduled for Phase 4)</span>
          </div>
        </div>
      </div>
    </div>
  );
}
