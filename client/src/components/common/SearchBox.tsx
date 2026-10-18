import React, { useState, useEffect, useRef } from 'react';
import { Search as SearchIcon, X, Clock, Sparkles, ChevronRight, Car, Compass } from 'lucide-react';
import { storageService, RecentSearchItem } from '../../services/storageService';
import { vehicleApi } from '../../api/vehicleApi';
import { DiscoveryCandidate, AutocompleteItem } from '../../types';

export interface SearchBoxProps {
  onSelectVehicle?: (vehicle: { brand: string; model: string; year?: number; canonical_id?: string }) => void;
  onSearch?: (query: string) => void;
  placeholder?: string;
  autoFocus?: boolean;
  size?: 'md' | 'lg';
}

const POPULAR_SUGGESTIONS = [
  { brand: 'Honda', model: 'City', year: 2021, canonical_id: 'honda::city' },
  { brand: 'Hyundai', model: 'Creta', year: 2020, canonical_id: 'hyundai::creta' },
  { brand: 'Maruti', model: 'Swift', year: 2019, canonical_id: 'maruti-suzuki::swift' },
  { brand: 'Tata', model: 'Nexon', year: 2021, canonical_id: 'tata::nexon' },
  { brand: 'Toyota', model: 'Innova Crysta', year: 2018, canonical_id: 'toyota::innova-crysta' },
  { brand: 'Mahindra', model: 'Thar', year: 2022, canonical_id: 'mahindra::thar' },
];

export const SearchBox: React.FC<SearchBoxProps> = ({
  onSelectVehicle,
  onSearch,
  placeholder = 'Search by brand, model, or year (e.g. Honda City 2021)...',
  autoFocus = false,
  size = 'lg',
}) => {
  const [query, setQuery] = useState('');
  const [isOpen, setIsOpen] = useState(false);
  const [recentSearches, setRecentSearches] = useState<RecentSearchItem[]>([]);
  const [candidates, setCandidates] = useState<DiscoveryCandidate[]>([]);
  const [autocompleteItems, setAutocompleteItems] = useState<AutocompleteItem[]>([]);
  const [isResolving, setIsResolving] = useState(false);
  const [selectedIndex, setSelectedIndex] = useState<number>(-1);

  const containerRef = useRef<HTMLDivElement>(null);
  const inputRef = useRef<HTMLInputElement>(null);

  useEffect(() => {
    setRecentSearches(storageService.getRecentSearches());
  }, []);

  // Close dropdown on outside click
  useEffect(() => {
    const handleOutsideClick = (e: MouseEvent) => {
      if (containerRef.current && !containerRef.current.contains(e.target as Node)) {
        setIsOpen(false);
      }
    };
    document.addEventListener('mousedown', handleOutsideClick);
    return () => document.removeEventListener('mousedown', handleOutsideClick);
  }, []);

  // Debounced taxonomy autocomplete and candidate resolution
  useEffect(() => {
    const trimmed = query.trim();
    if (trimmed.length < 2) {
      setCandidates([]);
      setAutocompleteItems([]);
      setIsResolving(false);
      setSelectedIndex(-1);
      return;
    }

    const timer = setTimeout(async () => {
      setIsResolving(true);
      try {
        const [acRes, searchRes] = await Promise.all([
          vehicleApi.autocomplete(trimmed, 5).catch(() => ({ query: trimmed, items: [] })),
          vehicleApi.searchVehicles({ q: trimmed, limit: 5 }).catch(() => null),
        ]);

        setAutocompleteItems(acRes.items || []);
        if (searchRes && searchRes.results) {
          setCandidates(searchRes.results);
        } else {
          setCandidates([]);
        }
      } catch {
        setCandidates([]);
        setAutocompleteItems([]);
      } finally {
        setIsResolving(false);
        setSelectedIndex(-1);
      }
    }, 200);

    return () => clearTimeout(timer);
  }, [query]);

  const handleSelect = (item: { brand: string; model: string; year?: number; canonical_id?: string }) => {
    storageService.addRecentSearch(item);
    setRecentSearches(storageService.getRecentSearches());
    setIsOpen(false);
    const selectedQuery = `${item.brand} ${item.model} ${item.year || ''}`.trim();
    setQuery(selectedQuery);
    if (onSelectVehicle) {
      onSelectVehicle(item);
    } else if (onSearch) {
      onSearch(selectedQuery);
    }
  };

  const totalSelectableCount = candidates.length + autocompleteItems.length;

  const handleKeyDown = (e: React.KeyboardEvent) => {
    if (e.key === 'ArrowDown') {
      e.preventDefault();
      if (!isOpen) {
        setIsOpen(true);
      } else if (totalSelectableCount > 0) {
        setSelectedIndex(prev => (prev + 1) % totalSelectableCount);
      }
    } else if (e.key === 'ArrowUp') {
      e.preventDefault();
      if (totalSelectableCount > 0) {
        setSelectedIndex(prev => (prev - 1 + totalSelectableCount) % totalSelectableCount);
      }
    } else if (e.key === 'Escape') {
      setIsOpen(false);
    } else if (e.key === 'Enter') {
      const trimmed = query.trim();
      if (!trimmed) return;

      if (selectedIndex >= 0 && selectedIndex < candidates.length) {
        const c = candidates[selectedIndex];
        handleSelect({
          brand: c.manufacturer,
          model: c.model,
          year: c.model_year,
          canonical_id: c.canonical_vehicle_id,
        });
      } else if (selectedIndex >= candidates.length && selectedIndex < totalSelectableCount) {
        const ac = autocompleteItems[selectedIndex - candidates.length];
        handleSelect({
          brand: ac.manufacturer || ac.title,
          model: ac.model || '',
          year: ac.year,
          canonical_id: ac.canonical_vehicle_id,
        });
      } else {
        setIsOpen(false);
        if (onSearch) {
          onSearch(trimmed);
        } else {
          const parts = trimmed.split(/\s+/);
          handleSelect({
            brand: parts[0] || '',
            model: parts.slice(1).join(' ') || '',
          });
        }
      }
    }
  };

  return (
    <div
      ref={containerRef}
      style={{ position: 'relative', width: '100%', maxWidth: '720px' }}
      className="carspective-search-container"
    >
      {/* Search Input Bar */}
      <div
        style={{
          display: 'flex',
          alignItems: 'center',
          backgroundColor: 'var(--bg-primary)',
          borderRadius: size === 'lg' ? 'var(--radius-xl)' : 'var(--radius-lg)',
          border: isOpen ? '2px solid var(--accent-blue)' : '1px solid var(--border-medium)',
          boxShadow: isOpen ? 'var(--shadow-lg)' : 'var(--shadow-md)',
          padding: size === 'lg' ? 'var(--space-3) var(--space-4)' : 'var(--space-2) var(--space-3)',
          transition: 'all var(--transition-fast)',
        }}
      >
        <SearchIcon
          size={size === 'lg' ? 22 : 18}
          color={isOpen ? 'var(--accent-blue)' : 'var(--text-muted)'}
          style={{ marginRight: 'var(--space-3)', flexShrink: 0 }}
        />

        <input
          ref={inputRef}
          role="combobox"
          type="text"
          value={query}
          onChange={e => {
            setQuery(e.target.value);
            setIsOpen(true);
          }}
          onFocus={() => setIsOpen(true)}
          onKeyDown={handleKeyDown}
          placeholder={placeholder}
          autoFocus={autoFocus}
          aria-label="Search vehicles by brand, model or year"
          aria-autocomplete="list"
          aria-expanded={isOpen}
          style={{
            flex: 1,
            border: 'none',
            outline: 'none',
            fontSize: size === 'lg' ? 'var(--font-size-lg)' : 'var(--font-size-base)',
            fontFamily: 'inherit',
            color: 'var(--text-primary)',
            background: 'transparent',
          }}
        />

        {query && (
          <button
            onClick={() => {
              setQuery('');
              setCandidates([]);
              setAutocompleteItems([]);
              inputRef.current?.focus();
            }}
            aria-label="Clear search query"
            style={{
              padding: 'var(--space-1)',
              color: 'var(--text-muted)',
              cursor: 'pointer',
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'center',
              border: 'none',
              background: 'transparent',
            }}
          >
            <X size={18} />
          </button>
        )}
      </div>

      {/* Dropdown Suggestions Panel */}
      {isOpen && (
        <div
          role="listbox"
          style={{
            position: 'absolute',
            top: 'calc(100% + 8px)',
            left: 0,
            right: 0,
            backgroundColor: 'var(--bg-primary)',
            borderRadius: 'var(--radius-xl)',
            border: '1px solid var(--border-subtle)',
            boxShadow: 'var(--shadow-xl)',
            maxHeight: '400px',
            overflowY: 'auto',
            zIndex: 500,
            padding: 'var(--space-3)',
            animation: 'fadeInScale 0.15s ease-out',
          }}
        >
          {/* Real-time Canonical Resolution Matches */}
          {candidates.length > 0 && (
            <div style={{ marginBottom: 'var(--space-3)' }}>
              <div
                style={{
                  fontSize: 'var(--font-size-xs)',
                  fontWeight: 'var(--font-weight-semibold)',
                  color: 'var(--text-muted)',
                  textTransform: 'uppercase',
                  letterSpacing: '0.05em',
                  padding: 'var(--space-1) var(--space-2)',
                }}
              >
                Canonical Vehicles Found
              </div>
              {candidates.map((c, idx) => {
                const isSelected = selectedIndex === idx;
                return (
                  <div
                    key={c.canonical_vehicle_id || idx}
                    role="option"
                    aria-selected={isSelected}
                    onClick={() =>
                      handleSelect({
                        brand: c.manufacturer,
                        model: c.model,
                        year: c.model_year,
                        canonical_id: c.canonical_vehicle_id,
                      })
                    }
                    style={{
                      display: 'flex',
                      alignItems: 'center',
                      justifyContent: 'space-between',
                      padding: 'var(--space-2) var(--space-3)',
                      borderRadius: 'var(--radius-md)',
                      cursor: 'pointer',
                      transition: 'background var(--transition-fast)',
                      backgroundColor: isSelected ? 'var(--bg-secondary)' : 'transparent',
                    }}
                    onMouseEnter={() => setSelectedIndex(idx)}
                  >
                    <div style={{ display: 'flex', flexDirection: 'column' }}>
                      <span style={{ fontWeight: 'var(--font-weight-semibold)', color: 'var(--text-primary)' }}>
                        {c.manufacturer} {c.model} ({c.model_year})
                      </span>
                      <span style={{ fontSize: 'var(--font-size-xs)', color: 'var(--text-muted)' }}>
                        {c.variant || 'Standard'} • {c.fuel_type || 'Petrol'} • {Math.round(c.match_score)}% match
                      </span>
                    </div>
                    <ChevronRight size={16} color="var(--text-subtle)" />
                  </div>
                );
              })}
            </div>
          )}

          {/* Taxonomy Autocomplete Items */}
          {autocompleteItems.length > 0 && (
            <div style={{ marginBottom: 'var(--space-3)' }}>
              <div
                style={{
                  fontSize: 'var(--font-size-xs)',
                  fontWeight: 'var(--font-weight-semibold)',
                  color: 'var(--text-muted)',
                  textTransform: 'uppercase',
                  letterSpacing: '0.05em',
                  padding: 'var(--space-1) var(--space-2)',
                }}
              >
                Taxonomy Suggestions
              </div>
              {autocompleteItems.map((item, acIdx) => {
                const globalIdx = candidates.length + acIdx;
                const isSelected = selectedIndex === globalIdx;
                return (
                  <div
                    key={item.id}
                    role="option"
                    aria-selected={isSelected}
                    onClick={() => {
                      if (item.type === 'vehicle' && item.canonical_vehicle_id) {
                        handleSelect({
                          brand: item.manufacturer || item.title,
                          model: item.model || '',
                          year: item.year,
                          canonical_id: item.canonical_vehicle_id,
                        });
                      } else {
                        setQuery(item.title);
                        if (onSelectVehicle) {
                          onSelectVehicle({
                            brand: item.manufacturer || item.title,
                            model: item.model || '',
                            year: item.year,
                          });
                        }
                      }
                    }}
                    style={{
                      display: 'flex',
                      alignItems: 'center',
                      justifyContent: 'space-between',
                      padding: 'var(--space-2) var(--space-3)',
                      borderRadius: 'var(--radius-md)',
                      cursor: 'pointer',
                      backgroundColor: isSelected ? 'var(--bg-secondary)' : 'transparent',
                    }}
                    onMouseEnter={() => setSelectedIndex(globalIdx)}
                  >
                    <div style={{ display: 'flex', alignItems: 'center', gap: 'var(--space-2)' }}>
                      <Car size={14} color="var(--accent-blue)" />
                      <span style={{ fontSize: 'var(--font-size-sm)', color: 'var(--text-primary)' }}>
                        {item.title}
                      </span>
                    </div>
                    {item.subtitle && (
                      <span style={{ fontSize: 'var(--font-size-xs)', color: 'var(--text-muted)' }}>
                        {item.subtitle}
                      </span>
                    )}
                  </div>
                );
              })}
            </div>
          )}

          {/* Loading indicator */}
          {isResolving && candidates.length === 0 && autocompleteItems.length === 0 && (
            <div style={{ padding: 'var(--space-3)', fontSize: 'var(--font-size-xs)', color: 'var(--text-muted)' }}>
              Resolving canonical taxonomy...
            </div>
          )}

          {/* Recent Searches */}
          {recentSearches.length > 0 && query.trim().length < 2 && (
            <div style={{ marginBottom: 'var(--space-3)' }}>
              <div
                style={{
                  display: 'flex',
                  justifyContent: 'space-between',
                  alignItems: 'center',
                  fontSize: 'var(--font-size-xs)',
                  fontWeight: 'var(--font-weight-semibold)',
                  color: 'var(--text-muted)',
                  textTransform: 'uppercase',
                  letterSpacing: '0.05em',
                  padding: 'var(--space-1) var(--space-2)',
                }}
              >
                <span>Recent Searches</span>
                <button
                  onClick={e => {
                    e.stopPropagation();
                    storageService.clearRecentSearches();
                    setRecentSearches([]);
                  }}
                  style={{
                    fontSize: 'var(--font-size-xs)',
                    color: 'var(--accent-blue)',
                    cursor: 'pointer',
                    background: 'transparent',
                    border: 'none',
                  }}
                >
                  Clear
                </button>
              </div>
              {recentSearches.map(item => (
                <div
                  key={item.id}
                  onClick={() => handleSelect(item)}
                  style={{
                    display: 'flex',
                    alignItems: 'center',
                    gap: 'var(--space-2)',
                    padding: 'var(--space-2) var(--space-3)',
                    borderRadius: 'var(--radius-md)',
                    cursor: 'pointer',
                    fontSize: 'var(--font-size-sm)',
                    color: 'var(--text-secondary)',
                  }}
                  onMouseEnter={e => (e.currentTarget.style.backgroundColor = 'var(--bg-secondary)')}
                  onMouseLeave={e => (e.currentTarget.style.backgroundColor = 'transparent')}
                >
                  <Clock size={14} color="var(--text-muted)" />
                  <span>
                    {item.brand} {item.model} {item.year ? `(${item.year})` : ''}
                  </span>
                </div>
              ))}
            </div>
          )}

          {/* Popular Suggestions */}
          {query.trim().length < 2 && (
            <div>
              <div
                style={{
                  fontSize: 'var(--font-size-xs)',
                  fontWeight: 'var(--font-weight-semibold)',
                  color: 'var(--text-muted)',
                  textTransform: 'uppercase',
                  letterSpacing: '0.05em',
                  padding: 'var(--space-1) var(--space-2)',
                }}
              >
                Popular Vehicles
              </div>
              <div style={{ display: 'flex', flexWrap: 'wrap', gap: 'var(--space-2)', padding: 'var(--space-1) var(--space-2)' }}>
                {POPULAR_SUGGESTIONS.map(s => (
                  <button
                    key={`${s.brand}-${s.model}-${s.year}`}
                    onClick={() => handleSelect(s)}
                    style={{
                      display: 'inline-flex',
                      alignItems: 'center',
                      gap: 'var(--space-1)',
                      backgroundColor: 'var(--bg-secondary)',
                      border: '1px solid var(--border-subtle)',
                      borderRadius: 'var(--radius-full)',
                      padding: 'var(--space-1) var(--space-3)',
                      fontSize: 'var(--font-size-xs)',
                      color: 'var(--text-primary)',
                      cursor: 'pointer',
                      transition: 'all var(--transition-fast)',
                    }}
                    onMouseEnter={e => (e.currentTarget.style.borderColor = 'var(--accent-blue)')}
                    onMouseLeave={e => (e.currentTarget.style.borderColor = 'var(--border-subtle)')}
                  >
                    <Sparkles size={12} color="var(--accent-blue)" />
                    <span>
                      {s.brand} {s.model} {s.year}
                    </span>
                  </button>
                ))}
              </div>
            </div>
          )}
        </div>
      )}
    </div>
  );
};
