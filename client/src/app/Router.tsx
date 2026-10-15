import React, { useState, useEffect } from 'react';
import { Layout } from './Layout';
import { HomePage } from '../pages/HomePage';
import { SearchPage } from '../pages/SearchPage';
import { VehiclePage } from '../pages/VehiclePage';
import { ValuationPage } from '../pages/ValuationPage';
import { DealPage } from '../pages/DealPage';
import { ComparisonPage } from '../pages/ComparisonPage';
import { InspectionPage } from '../pages/InspectionPage';

export const Router: React.FC = () => {
  const getInitialPath = () => {
    if (typeof window === 'undefined') return '/';
    const hash = window.location.hash.replace(/^#/, '');
    if (hash) return hash;
    return window.location.pathname || '/';
  };

  const [currentPath, setCurrentPath] = useState<string>(getInitialPath);

  useEffect(() => {
    const handlePopState = () => {
      const hash = window.location.hash.replace(/^#/, '');
      setCurrentPath(hash || window.location.pathname || '/');
    };

    window.addEventListener('popstate', handlePopState);
    window.addEventListener('hashchange', handlePopState);
    return () => {
      window.removeEventListener('popstate', handlePopState);
      window.removeEventListener('hashchange', handlePopState);
    };
  }, []);

  const navigate = (path: string) => {
    if (path.startsWith('/')) {
      window.location.hash = path;
      setCurrentPath(path);
      window.scrollTo(0, 0);
    }
  };

  const renderRoute = () => {
    // Strip hash prefix and query string
    const clean = currentPath.split('?')[0];

    if (clean === '/' || clean === '') {
      return <HomePage onNavigate={navigate} />;
    }
    if (clean === '/search') {
      return <SearchPage onNavigate={navigate} />;
    }
    if (clean.startsWith('/vehicle')) {
      const vehicleId = clean.replace('/vehicle/', '');
      return <VehiclePage vehicleId={vehicleId} onNavigate={navigate} />;
    }
    if (clean === '/value') {
      return <ValuationPage />;
    }
    if (clean === '/deal') {
      return <DealPage />;
    }
    if (clean === '/compare') {
      return <ComparisonPage />;
    }
    if (clean === '/inspect') {
      return <InspectionPage />;
    }

    // Default fallback to HomePage
    return <HomePage onNavigate={navigate} />;
  };

  return (
    <Layout currentPath={currentPath} onNavigate={navigate}>
      {renderRoute()}
    </Layout>
  );
};
