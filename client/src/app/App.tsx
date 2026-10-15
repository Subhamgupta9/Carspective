import React from 'react';
import { AppProvider } from '../state/AppContext';
import { Router } from './Router';

export const App: React.FC = () => {
  return (
    <AppProvider>
      <Router />
    </AppProvider>
  );
};

export default App;
