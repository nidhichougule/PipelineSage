import React, { useState } from 'react';
import Sidebar from './components/Sidebar';
import Header from './components/Header';
import Dashboard from './pages/Dashboard';
import WorkflowRuns from './pages/WorkflowRuns';
import Diagnosis from './pages/Diagnosis';
import Settings from './pages/Settings';

export default function App() {
  const [activeTab, setActiveTab] = useState('dashboard');
  const [selectedRunId, setSelectedRunId] = useState(null);

  const handleSelectRun = (runId) => {
    setSelectedRunId(runId);
    setActiveTab('diagnosis');
  };

  const getPageTitle = () => {
    switch (activeTab) {
      case 'dashboard':
        return 'Engineering Overview & Health';
      case 'runs':
        return 'Workflow Runs';
      case 'diagnosis':
        return selectedRunId ? `Diagnosis for Run #${selectedRunId}` : 'Failure Diagnosis';
      case 'settings':
        return 'Repository & Engine Settings';
      default:
        return 'PipelineSage';
    }
  };

  return (
    <div className="app-container">
      <Sidebar activeTab={activeTab} setActiveTab={setActiveTab} />
      <div className="main-wrapper">
        <Header title={getPageTitle()} />
        <main className="content-body">
          {activeTab === 'dashboard' && <Dashboard onSelectRun={handleSelectRun} />}
          {activeTab === 'runs' && <WorkflowRuns onSelectRun={handleSelectRun} />}
          {activeTab === 'diagnosis' && <Diagnosis onBack={() => setActiveTab('runs')} />}
          {activeTab === 'settings' && <Settings />}
        </main>
      </div>
    </div>
  );
}
