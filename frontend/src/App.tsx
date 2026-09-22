import React, { useState } from 'react';
import Header from './components/layout/Header';
import SearchPanel from './components/search/SearchPanel';
import AnswerPanel from './components/search/AnswerPanel';
import MetricsDashboard from './components/dashboard/MetricsDashboard';
import { useSearch } from './hooks/useSearch';
import ServerStatusBanner from './components/layout/ServerStatusBanner';
import { useServerStatus } from './hooks/useServerStatus';

type Tab = 'search' | 'dashboard';

const App: React.FC = () => {
  const [tab, setTab] = useState<Tab>('search');
  const { question, setQuestion, searching, streamText, sources, result, streaming, error, search } = useSearch();
  const { status, elapsedSec } = useServerStatus();
  const serverReady = status === 'ready';

  return (
    <div style={{ minHeight: '100vh', background: '#0f0f1a', color: '#e0e0e0' }}>
      <Header activeTab={tab} onTabChange={setTab} />
      <ServerStatusBanner status={status} elapsedSec={elapsedSec} />

      <main style={{ maxWidth: 1100, margin: '0 auto', padding: '32px 24px' }}>
        {tab === 'search' ? (
          <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 32 }}>
            <SearchPanel
              serverReady={serverReady}
              question={question}
              onQuestionChange={setQuestion}
              onSearch={search}
              searching={searching}
              searchError={error}
            />
            <AnswerPanel
              streamText={streamText}
              sources={sources}
              result={result}
              streaming={streaming}
            />
          </div>
        ) : (
          <MetricsDashboard serverReady={serverReady} />
        )}
      </main>
    </div>
  );
};

export default App;
