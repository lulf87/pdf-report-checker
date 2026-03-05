import { useState } from 'react';
import { Header } from '../../components/layout';
import { PTRUpload } from './PTRUpload';
import { PTRResults } from './PTRResults';
import type { PTRCompareResult } from '../../types/ptr';

type PageState = 'upload' | 'results';

interface ResultWithTaskId {
  result: PTRCompareResult;
  taskId: string;
  generatedAtMs: number;
}

/**
 * PTRComparePage - Main page for PTR clause comparison
 *
 * State management:
 * - upload: Show file upload interface
 * - results: Show comparison results
 */
export function PTRComparePage() {
  const [pageState, setPageState] = useState<PageState>('upload');
  const [resultData, setResultData] = useState<ResultWithTaskId | null>(null);

  const handleComplete = (compareResult: PTRCompareResult, taskId: string) => {
    setResultData({ result: compareResult, taskId, generatedAtMs: Date.now() });
    setPageState('results');
  };

  const handleBack = () => {
    if (pageState === 'results') {
      setPageState('upload');
      setResultData(null);
    }
  };

  const handleReupload = () => {
    setPageState('upload');
    setResultData(null);
  };

  const handleDashboard = () => {
    window.location.hash = '/';
  };

  return (
    <>
      <Header
        title="PTR 条款核对"
        onBack={pageState === 'results' ? handleBack : handleDashboard}
        showBack={true}
      />

      <main
        style={{
          minHeight: '100vh',
          paddingTop: '80px',
        }}
      >
        {pageState === 'upload' && (
          <PTRUpload
            key="upload"
            onComplete={handleComplete}
            onBack={handleDashboard}
          />
        )}

        {pageState === 'results' && resultData && (
          <PTRResults
            key="results"
            result={resultData.result}
            taskId={resultData.taskId}
            generatedAtMs={resultData.generatedAtMs}
            onBack={handleBack}
            onReupload={handleReupload}
            onDashboard={handleDashboard}
          />
        )}
      </main>
    </>
  );
}
