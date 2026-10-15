import React from 'react';
import { Header } from './Header';
import { Footer } from './Footer';
import { AssistantDrawer } from '../features/assistant/AssistantDrawer';

export interface LayoutProps {
  currentPath: string;
  onNavigate: (path: string) => void;
  children: React.ReactNode;
}

export const Layout: React.FC<LayoutProps> = ({ currentPath, onNavigate, children }) => {
  return (
    <div style={{ display: 'flex', flexDirection: 'column', minHeight: '100vh', width: '100%' }}>
      <Header currentPath={currentPath} onNavigate={onNavigate} />

      <main style={{ flex: 1, display: 'flex', flexDirection: 'column' }}>
        {children}
      </main>

      <Footer />

      {/* Persistent AI Assistant Drawer */}
      <AssistantDrawer />
    </div>
  );
};
