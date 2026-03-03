import { useState, useEffect } from 'react';
import { Background, MouseFollower } from './components/layout';
import { Dashboard, PTRComparePage, ReportCheckPage } from './pages';
import './styles/design-tokens.css';

function App() {
  const [hash, setHash] = useState(() => window.location.hash || '#/');

  useEffect(() => {
    const handleHashChange = () => {
      setHash(window.location.hash || '#/');
    };

    window.addEventListener('hashchange', handleHashChange);
    return () => window.removeEventListener('hashchange', handleHashChange);
  }, []);

  const path = hash.replace('#', '') || '/';

  const renderPage = () => {
    switch (path) {
      case '/':
      case '':
        return <Dashboard />;
      case '/ptr-compare':
        return <PTRComparePage />;
      case '/report-check':
        return <ReportCheckPage />;
      default:
        return <Dashboard />;
    }
  };

  return (
    <>
      <Background />
      <MouseFollower />
      {renderPage()}
    </>
  );
}

export default App;
