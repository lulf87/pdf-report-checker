import { useState } from 'react';
import { Header } from '../../components/layout';
import { ReportUpload } from './ReportUpload';
import { ReportResults } from './ReportResults';
import type { ReportCheckResult } from '../../types/report';

type PageState = 'upload' | 'results';

/**
 * ReportCheckPage - Main page for report self-check functionality
 *
 * Features:
 * - Upload single report PDF
 * - View check results with field comparisons
 * - Navigate back to Dashboard
 */
export function ReportCheckPage() {
  const [pageState, setPageState] = useState<PageState>('upload');
  const [result, setResult] = useState<ReportCheckResult | null>(null);

  const handleResults = (checkResult: ReportCheckResult) => {
    setResult(checkResult);
    setPageState('results');
  };

  const handleReupload = () => {
    setResult(null);
    setPageState('upload');
  };

  const handleBack = () => {
    window.location.hash = '#/';
  };

  return (
    <>
      <Header
        title="报告自身核对"
        onBack={handleBack}
        showBack={pageState === 'upload'}
      />
      <main style={{ paddingTop: '80px' }}>
        {pageState === 'upload' && (
          <ReportUpload
            key="upload"
            onResults={handleResults}
          />
        )}
        {pageState === 'results' && result && (
          <ReportResults
            key="results"
            result={result}
            onReupload={handleReupload}
            onDashboard={handleBack}
          />
        )}
      </main>
    </>
  );
}
