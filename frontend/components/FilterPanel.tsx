'use client';

import { useState, useEffect } from 'react';
import { X, ChevronDown, ChevronUp } from 'lucide-react';
import { getKeywords } from '@/lib/apiClient';

export interface FilterState {
  sourceType: 'all' | 'dataset' | 'mine';
  keywords: string[];
  maxCalories: number;
  minProtein: number;
  maxCarbs: number;
  maxFat: number;
  servings?: number;
}

interface FilterPanelProps {
  isOpen: boolean;
  onClose: () => void;
  filters: FilterState;
  onFiltersChange: (filters: FilterState) => void;
}

export default function FilterPanel({ isOpen, onClose, filters, onFiltersChange }: FilterPanelProps) {
  const [allKeywords, setAllKeywords] = useState<string[]>([]);
  const [showAllKeywords, setShowAllKeywords] = useState(false);
  const [expandedSections, setExpandedSections] = useState({
    source: true,
    keywords: true,
    nutrition: false,
    other: false,
  });

  useEffect(() => {
    const fetchFilterData = async () => {
      try {
        const keywords = await getKeywords();
        setAllKeywords(keywords);
      } catch (error) {
        console.error('Failed to fetch filter data:', error);
      }
    };

    fetchFilterData();
  }, []);

  const toggleSection = (section: keyof typeof expandedSections) => {
    setExpandedSections(prev => ({ ...prev, [section]: !prev[section] }));
  };

  const updateFilter = (key: keyof FilterState, value: any) => {
    onFiltersChange({ ...filters, [key]: value });
  };

  const toggleKeyword = (keyword: string) => {
    const newKeywords = filters.keywords.includes(keyword)
      ? filters.keywords.filter(k => k !== keyword)
      : [...filters.keywords, keyword];
    updateFilter('keywords', newKeywords);
  };

  const clearFilters = () => {
    onFiltersChange({
      sourceType: 'all',
      keywords: [],
      maxCalories: 2000,
      minProtein: 0,
      maxCarbs: 300,
      maxFat: 100,
    });
  };

  const hasActiveFilters = 
    filters.sourceType !== 'all' ||
    filters.keywords.length > 0 ||
    filters.maxCalories !== 2000 ||
    filters.minProtein !== 0 ||
    filters.maxCarbs !== 300 ||
    filters.maxFat !== 100;

  // Group keywords by type
  const groupedKeywords = {
    dietary: allKeywords.filter(k => 
      ['vegetarian', 'vegan', 'gluten-free', 'lactose free', 'dairy-free'].some(d => 
        k.toLowerCase().includes(d)
      )
    ),
    health: allKeywords.filter(k => 
      ['low', 'high', 'healthy', 'protein', 'calorie', 'carb', 'fat'].some(h => 
        k.toLowerCase().includes(h)
      )
    ),
    time: allKeywords.filter(k => 
      ['min', 'mins', 'quick', 'weeknight', 'easy', 'beginner'].some(t => 
        k.toLowerCase().includes(t)
      )
    ),
  };

  if (!isOpen) return null;

  return (
    <>
      {/* Backdrop */}
      <div 
        className="fixed inset-0 bg-black/50 z-40 md:hidden"
        onClick={onClose}
      />

      {/* Panel */}
      <div className="fixed md:static inset-y-0 left-0 w-80 bg-white border-r border-gray-200 overflow-y-auto z-50 transform transition-transform md:transform-none">
        {/* Header */}
        <div className="sticky top-0 bg-white border-b border-gray-200 px-4 py-4 flex items-center justify-between">
          <h2 className="text-lg font-semibold text-gray-900">Filters</h2>
          <div className="flex items-center gap-2">
            {hasActiveFilters && (
              <button
                onClick={clearFilters}
                className="text-sm text-emerald-600 hover:text-emerald-700"
              >
                Clear All
              </button>
            )}
            <button onClick={onClose} className="md:hidden p-1 hover:bg-gray-100 rounded">
              <X size={20} />
            </button>
          </div>
        </div>

        {/* Filter Sections */}
        <div className="p-4 space-y-6">
          {/* Source Type */}
          <div>
            <button
              onClick={() => toggleSection('source')}
              className="flex items-center justify-between w-full mb-3"
            >
              <h3 className="font-semibold text-gray-900">Source</h3>
              {expandedSections.source ? <ChevronUp size={16} /> : <ChevronDown size={16} />}
            </button>
            
            {expandedSections.source && (
              <div className="space-y-2">
                <label className="flex items-center gap-2 cursor-pointer">
                  <input
                    type="radio"
                    checked={filters.sourceType === 'all'}
                    onChange={() => updateFilter('sourceType', 'all')}
                    className="w-4 h-4 text-emerald-600"
                  />
                  <span className="text-sm text-gray-700">All Recipes</span>
                </label>
                <label className="flex items-center gap-2 cursor-pointer">
                  <input
                    type="radio"
                    checked={filters.sourceType === 'dataset'}
                    onChange={() => updateFilter('sourceType', 'dataset')}
                    className="w-4 h-4 text-emerald-600"
                  />
                  <span className="text-sm text-gray-700">Dataset Recipes</span>
                  <span className="px-2 py-0.5 bg-blue-50 text-blue-700 rounded text-xs">
                    {allKeywords.length > 0 ? `${allKeywords.length} tags` : ''}
                  </span>
                </label>
                <label className="flex items-center gap-2 cursor-pointer">
                  <input
                    type="radio"
                    checked={filters.sourceType === 'mine'}
                    onChange={() => updateFilter('sourceType', 'mine')}
                    className="w-4 h-4 text-emerald-600"
                  />
                  <span className="text-sm text-gray-700">My Recipes</span>
                </label>
              </div>
            )}
          </div>

          {/* Keywords */}
          <div>
            <button
              onClick={() => toggleSection('keywords')}
              className="flex items-center justify-between w-full mb-3"
            >
              <h3 className="font-semibold text-gray-900">Tags</h3>
              {expandedSections.keywords ? <ChevronUp size={16} /> : <ChevronDown size={16} />}
            </button>
            
            {expandedSections.keywords && (
              <div className="space-y-3">
                {/* Dietary */}
                {groupedKeywords.dietary.length > 0 && (
                  <div>
                    <h4 className="text-xs font-medium text-gray-500 mb-2">Dietary</h4>
                    <div className="flex flex-wrap gap-2">
                      {groupedKeywords.dietary.slice(0, showAllKeywords ? undefined : 10).map(keyword => (
                        <button
                          key={keyword}
                          onClick={() => toggleKeyword(keyword)}
                          className={`px-3 py-1 rounded-full text-xs font-medium transition-colors ${
                            filters.keywords.includes(keyword)
                              ? 'bg-emerald-100 text-emerald-700 border border-emerald-300'
                              : 'bg-gray-100 text-gray-700 hover:bg-gray-200'
                          }`}
                        >
                          {keyword}
                        </button>
                      ))}
                    </div>
                  </div>
                )}

                {/* Health */}
                {groupedKeywords.health.length > 0 && (
                  <div>
                    <h4 className="text-xs font-medium text-gray-500 mb-2">Health</h4>
                    <div className="flex flex-wrap gap-2">
                      {groupedKeywords.health.slice(0, showAllKeywords ? undefined : 10).map(keyword => (
                        <button
                          key={keyword}
                          onClick={() => toggleKeyword(keyword)}
                          className={`px-3 py-1 rounded-full text-xs font-medium transition-colors ${
                            filters.keywords.includes(keyword)
                              ? 'bg-emerald-100 text-emerald-700 border border-emerald-300'
                              : 'bg-gray-100 text-gray-700 hover:bg-gray-200'
                          }`}
                        >
                          {keyword}
                        </button>
                      ))}
                    </div>
                  </div>
                )}

                {/* Time */}
                {groupedKeywords.time.length > 0 && (
                  <div>
                    <h4 className="text-xs font-medium text-gray-500 mb-2">Time & Difficulty</h4>
                    <div className="flex flex-wrap gap-2">
                      {groupedKeywords.time.slice(0, showAllKeywords ? undefined : 10).map(keyword => (
                        <button
                          key={keyword}
                          onClick={() => toggleKeyword(keyword)}
                          className={`px-3 py-1 rounded-full text-xs font-medium transition-colors ${
                            filters.keywords.includes(keyword)
                              ? 'bg-emerald-100 text-emerald-700 border border-emerald-300'
                              : 'bg-gray-100 text-gray-700 hover:bg-gray-200'
                          }`}
                        >
                          {keyword}
                        </button>
                      ))}
                    </div>
                  </div>
                )}

                {allKeywords.length > 30 && (
                  <button
                    onClick={() => setShowAllKeywords(!showAllKeywords)}
                    className="text-sm text-emerald-600 hover:text-emerald-700"
                  >
                    {showAllKeywords ? 'Show Less' : `Show All Keywords`}
                  </button>
                )}
              </div>
            )}
          </div>

          {/* Nutrition */}
          <div>
            <button
              onClick={() => toggleSection('nutrition')}
              className="flex items-center justify-between w-full mb-3"
            >
              <h3 className="font-semibold text-gray-900">Nutrition</h3>
              {expandedSections.nutrition ? <ChevronUp size={16} /> : <ChevronDown size={16} />}
            </button>
            
            {expandedSections.nutrition && (
              <div className="space-y-4">
                <div>
                  <label className="text-sm text-gray-700 mb-2 flex items-center justify-between">
                    <span>Max Calories</span>
                    <span className="font-medium">{filters.maxCalories}</span>
                  </label>
                  <input
                    type="range"
                    min="0"
                    max="2000"
                    step="50"
                    value={filters.maxCalories}
                    onChange={(e) => updateFilter('maxCalories', parseInt(e.target.value))}
                    className="w-full"
                  />
                </div>
                <div>
                  <label className="text-sm text-gray-700 mb-2 flex items-center justify-between">
                    <span>Min Protein (g)</span>
                    <span className="font-medium">{filters.minProtein}</span>
                  </label>
                  <input
                    type="range"
                    min="0"
                    max="100"
                    step="5"
                    value={filters.minProtein}
                    onChange={(e) => updateFilter('minProtein', parseInt(e.target.value))}
                    className="w-full"
                  />
                </div>
                <div>
                  <label className="text-sm text-gray-700 mb-2 flex items-center justify-between">
                    <span>Max Carbs (g)</span>
                    <span className="font-medium">{filters.maxCarbs}</span>
                  </label>
                  <input
                    type="range"
                    min="0"
                    max="300"
                    step="10"
                    value={filters.maxCarbs}
                    onChange={(e) => updateFilter('maxCarbs', parseInt(e.target.value))}
                    className="w-full"
                  />
                </div>
                <div>
                  <label className="text-sm text-gray-700 mb-2 flex items-center justify-between">
                    <span>Max Fat (g)</span>
                    <span className="font-medium">{filters.maxFat}</span>
                  </label>
                  <input
                    type="range"
                    min="0"
                    max="100"
                    step="5"
                    value={filters.maxFat}
                    onChange={(e) => updateFilter('maxFat', parseInt(e.target.value))}
                    className="w-full"
                  />
                </div>
              </div>
            )}
          </div>
        </div>
      </div>
    </>
  );
}
