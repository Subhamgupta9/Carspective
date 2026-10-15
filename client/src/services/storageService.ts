/**
 * CARspective — Client Storage Service
 * Handles anonymous local persistence for recent searches, saved comparison selections,
 * and user preferences. No sensitive personal data or credentials stored.
 */

const STORAGE_KEYS = {
  RECENT_SEARCHES: 'carspective_recent_searches',
  SAVED_VEHICLES: 'carspective_saved_vehicles',
  COMPARISON_SELECTION: 'carspective_comparison_selection',
  USER_PREFERENCES: 'carspective_user_prefs',
};

export interface RecentSearchItem {
  id: string;
  brand: string;
  model: string;
  year?: number;
  timestamp: number;
}

export const storageService = {
  getRecentSearches: (): RecentSearchItem[] => {
    try {
      const data = localStorage.getItem(STORAGE_KEYS.RECENT_SEARCHES);
      return data ? JSON.parse(data) : [];
    } catch {
      return [];
    }
  },

  addRecentSearch: (item: Omit<RecentSearchItem, 'timestamp' | 'id'>): void => {
    try {
      const list = storageService.getRecentSearches();
      const id = `${item.brand}_${item.model}_${item.year || ''}`.toLowerCase();
      const updated = [
        { ...item, id, timestamp: Date.now() },
        ...list.filter(x => x.id !== id),
      ].slice(0, 8); // Keep top 8 recent searches
      localStorage.setItem(STORAGE_KEYS.RECENT_SEARCHES, JSON.stringify(updated));
    } catch {
      // Storage unavailable or disabled
    }
  },

  clearRecentSearches: (): void => {
    try {
      localStorage.removeItem(STORAGE_KEYS.RECENT_SEARCHES);
    } catch {
      // ignore
    }
  },

  getComparisonList: (): Array<{ brand: string; model: string; year?: number }> => {
    try {
      const data = localStorage.getItem(STORAGE_KEYS.COMPARISON_SELECTION);
      return data ? JSON.parse(data) : [];
    } catch {
      return [];
    }
  },

  setComparisonList: (vehicles: Array<{ brand: string; model: string; year?: number }>): void => {
    try {
      localStorage.setItem(STORAGE_KEYS.COMPARISON_SELECTION, JSON.stringify(vehicles.slice(0, 3)));
    } catch {
      // ignore
    }
  },
};
