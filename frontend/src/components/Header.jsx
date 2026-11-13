import React from 'react';

export default function Header({ title }) {
  return (
    <header className="header">
      <div className="header-title">
        <h2>{title}</h2>
      </div>
      <div className="header-meta">
        <div className="repo-pill">
          <span className="status-dot"></span>
          <span>nidhichougule/PipelineSage</span>
        </div>
        <span>CI Runner: Ubuntu-22.04</span>
      </div>
    </header>
  );
}
