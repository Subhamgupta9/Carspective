import React, { createContext, useContext, useState, useEffect } from 'react';
import { storageService } from '../services/storageService';
import { Toast } from '../components/common/Toast';

export interface VehicleSelection {
  canonical_id?: string;
  brand: string;
  model: string;
  year?: number;
  variant?: string;
  fuel_type?: string;
  transmission_type?: string;
  asking_price?: number;
  km_driven?: number;
}

export interface ToastItem {
  id: string;
  type: 'success' | 'error' | 'info';
  message: string;
}

export interface AppContextType {
  // Current vehicle
  currentVehicle: VehicleSelection | null;
  setCurrentVehicle: (vehicle: VehicleSelection | null) => void;

  // Comparison tray (2-3 vehicles)
  comparisonVehicles: VehicleSelection[];
  addComparisonVehicle: (vehicle: VehicleSelection) => boolean;
  removeComparisonVehicle: (index: number) => void;
  clearComparison: () => void;

  // AI Assistant Drawer
  isAssistantOpen: boolean;
  assistantPrompt: string;
  setAssistantPrompt: (prompt: string) => void;
  openAssistant: () => void;
  closeAssistant: () => void;
  toggleAssistant: () => void;

  // Notifications
  toasts: ToastItem[];
  showToast: (message: string, type?: 'success' | 'error' | 'info') => void;
  dismissToast: (id: string) => void;
}

const AppContext = createContext<AppContextType | undefined>(undefined);

export const AppProvider: React.FC<{ children: React.ReactNode }> = ({ children }) => {
  const [currentVehicle, setCurrentVehicle] = useState<VehicleSelection | null>(() => {
    // Default initial sample vehicle
    return {
      brand: 'Honda',
      model: 'City',
      year: 2021,
      variant: 'V',
      fuel_type: 'Petrol',
      transmission_type: 'Manual',
      asking_price: 850000,
      km_driven: 32000,
    };
  });

  const [comparisonVehicles, setComparisonVehicles] = useState<VehicleSelection[]>(() => {
    const saved = storageService.getComparisonList();
    if (saved && saved.length > 0) return saved;
    return [
      { brand: 'Honda', model: 'City', year: 2021 },
      { brand: 'Hyundai', model: 'Creta', year: 2020 },
    ];
  });

  const [isAssistantOpen, setIsAssistantOpen] = useState(false);
  const [assistantPrompt, setAssistantPrompt] = useState('');
  const [toasts, setToasts] = useState<ToastItem[]>([]);

  // Keep storage in sync
  useEffect(() => {
    storageService.setComparisonList(
      comparisonVehicles.map(v => ({ brand: v.brand, model: v.model, year: v.year }))
    );
  }, [comparisonVehicles]);

  const addComparisonVehicle = (vehicle: VehicleSelection): boolean => {
    if (comparisonVehicles.length >= 3) {
      showToast('Maximum 3 vehicles can be compared simultaneously.', 'info');
      return false;
    }
    const exists = comparisonVehicles.some(
      v => v.brand.toLowerCase() === vehicle.brand.toLowerCase() && v.model.toLowerCase() === vehicle.model.toLowerCase()
    );
    if (exists) {
      showToast(`${vehicle.brand} ${vehicle.model} is already in comparison.`, 'info');
      return false;
    }
    setComparisonVehicles(prev => [...prev, vehicle]);
    showToast(`Added ${vehicle.brand} ${vehicle.model} to comparison.`, 'success');
    return true;
  };

  const removeComparisonVehicle = (index: number) => {
    setComparisonVehicles(prev => prev.filter((_, i) => i !== index));
  };

  const clearComparison = () => {
    setComparisonVehicles([]);
  };

  const showToast = (message: string, type: 'success' | 'error' | 'info' = 'info') => {
    const id = `${Date.now()}_${Math.random()}`;
    setToasts(prev => [...prev, { id, type, message }]);
  };

  const dismissToast = (id: string) => {
    setToasts(prev => prev.filter(t => t.id !== id));
  };

  return (
    <AppContext.Provider
      value={{
        currentVehicle,
        setCurrentVehicle,
        comparisonVehicles,
        addComparisonVehicle,
        removeComparisonVehicle,
        clearComparison,
        isAssistantOpen,
        assistantPrompt,
        setAssistantPrompt,
        openAssistant: () => setIsAssistantOpen(true),
        closeAssistant: () => setIsAssistantOpen(false),
        toggleAssistant: () => setIsAssistantOpen(prev => !prev),
        toasts,
        showToast,
        dismissToast,
      }}
    >
      {children}

      {/* Floating Toast Container */}
      <div
        style={{
          position: 'fixed',
          bottom: 'var(--space-6)',
          right: 'var(--space-6)',
          display: 'flex',
          flexDirection: 'column',
          gap: 'var(--space-2)',
          zIndex: 2000,
          pointerEvents: 'none',
        }}
      >
        {toasts.map(t => (
          <div key={t.id} style={{ pointerEvents: 'auto' }}>
            <Toast id={t.id} type={t.type} message={t.message} onDismiss={dismissToast} />
          </div>
        ))}
      </div>
    </AppContext.Provider>
  );
};

export const useApp = (): AppContextType => {
  const context = useContext(AppContext);
  if (!context) {
    throw new Error('useApp must be used within an AppProvider');
  }
  return context;
};
