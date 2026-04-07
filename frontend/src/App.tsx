import React, { useState } from 'react';
import Header from './components/layout/Header';
import SearchPanel from './components/search/SearchPanel';
import AnswerPanel from './components/search/AnswerPanel';
import MetricsDashboard from './components/dashboard/MetricsDashboard';
import { useSearch } from './hooks/useSearch';

type Tab = 'search' | 'dashboard';

const App: React.FC = () => {
  const [tab, setTab] = useState<Tab>('search');
  const { question, setQuestion, searching, streamText, sources, result, streaming, error, search } = useSearch();

  return (
    <div style={{ minHeight: '100vh', background: '#0f0f1a', color: '#e0e0e0' }}>
      <Header activeTab={tab} onTabChange={setTab} />

      <main style={{ maxWidth: 1100, margin: '0 auto', padding: '32px 24px' }}>
        {tab === 'search' ? (
          <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 32 }}>
            <SearchPanel
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
          <MetricsDashboard />
        )}
      </main>
    </div>
  );
};

export default App;
