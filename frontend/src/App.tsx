import { useState } from 'react';
import { ConfigProvider } from 'antd';
import zhCN from 'antd/locale/zh_CN';
import UploadPage from './pages/UploadPage';
import ResultsPage from './pages/ResultsPage';

function App() {
  const [currentPage, setCurrentPage] = useState<'upload' | 'results'>('upload');

  return (
    <ConfigProvider
      locale={zhCN}
      theme={{
        token: {
          colorPrimary: '#3B82F6',
          colorSuccess: '#10B981',
          colorWarning: '#F59E0B',
          colorError: '#EF4444',
          borderRadius: 8,
        },
      }}
    >
      {currentPage === 'upload' ? (
        <UploadPage onComplete={() => setCurrentPage('results')} />
      ) : (
        <ResultsPage onBack={() => setCurrentPage('upload')} />
      )}
    </ConfigProvider>
  );
}

export default App;
