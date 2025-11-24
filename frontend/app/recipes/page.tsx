'use client';

import { useState, useEffect } from 'react';
import { Search, Filter, Grid3x3, List, X } from 'lucide-react';
import FilterPanel, { FilterState } from '@/components/FilterPanel';
import RecipeCard from '@/components/RecipeCard';
import RecipeDetailModal from '@/components/RecipeDetailModal';
import { searchRecipes, getRecipeById, RecipeSearchResult, RecipeSearchFilters } from '@/lib/apiClient';

export default function RecipesPage() {
  const [viewMode, setViewMode] = useState<'grid' | 'list'>('grid');
  const [searchQuery, setSearchQuery] = useState('');
  const [isFilterOpen, setIsFilterOpen] = useState(false);
  const [recipes, setRecipes] = useState<RecipeSearchResult[]>([]);
  const [isLoading, setIsLoading] = useState(false);
  const [selectedRecipe, setSelectedRecipe] = useState<any>(null);
  const [favorites, setFavorites] = useState<Set<string>>(new Set());
  const [currentPage, setCurrentPage] = useState(1);
  const [totalRecipes, setTotalRecipes] = useState(0);
  const [isInitialized, setIsInitialized] = useState(false);
  const recipesPerPage = 50;
  
  const [filters, setFilters] = useState<FilterState>({
    sourceType: 'all',
    keywords: [],
    maxCalories: 2000,
    minProtein: 0,
    maxCarbs: 300,
    maxFat: 100,
  });

  // Load state from session storage on mount
  useEffect(() => {
    const savedState = sessionStorage.getItem('recipeState');
    if (savedState) {
      try {
        const parsed = JSON.parse(savedState);
        setSearchQuery(parsed.searchQuery || '');
        setFilters(parsed.filters || {
          sourceType: 'all',
          keywords: [],
          maxCalories: 2000,
          minProtein: 0,
          maxCarbs: 300,
          maxFat: 100,
        });
        setCurrentPage(parsed.currentPage || 1);
        setRecipes(parsed.recipes || []);
        setTotalRecipes(parsed.totalRecipes || 0);
        setViewMode(parsed.viewMode || 'grid');
      } catch (e) {
        console.error("Failed to parse saved state", e);
      }
    }
    setIsInitialized(true);
  }, []);

  // Save state to session storage
  useEffect(() => {
    if (!isInitialized) return;
    const state = {
      searchQuery,
      filters,
      currentPage,
      recipes,
      totalRecipes,
      viewMode
    };
    sessionStorage.setItem('recipeState', JSON.stringify(state));
  }, [searchQuery, filters, currentPage, recipes, totalRecipes, viewMode, isInitialized]);

  // Fetch recipes when filters or search changes
  useEffect(() => {
    if (!isInitialized) return;

    const fetchRecipes = async () => {
      setIsLoading(true);
      try {
        const searchFilters: RecipeSearchFilters = {
          search: searchQuery || undefined,
          source_type: filters.sourceType === 'all' ? undefined : filters.sourceType,
          keywords: filters.keywords.length > 0 ? filters.keywords : undefined,
          max_calories: filters.maxCalories !== 2000 ? filters.maxCalories : undefined,
          min_protein: filters.minProtein > 0 ? filters.minProtein : undefined,
          max_carbs: filters.maxCarbs !== 300 ? filters.maxCarbs : undefined,
          max_fat: filters.maxFat !== 100 ? filters.maxFat : undefined,
          page: currentPage,
          limit: recipesPerPage,
        };
        
        const result = await searchRecipes(searchFilters);
        setRecipes(result.recipes);
        setTotalRecipes(result.total);
      } catch (error) {
        console.error('Failed to fetch recipes:', error);
        // Use placeholder data on error
        if (recipes.length === 0) {
          setRecipes([
            {
              id: '1',
              name: 'Grilled Chicken Salad',
              source: 'dataset',
              calories: 450,
              protein: 35,
              carbs: 25,
              fat: 18,
              time: 30,
              servings: 2,
              keywords: ['Healthy', 'High Protein', 'Quick'],
            },
            {
              id: '2',
              name: 'Chocolate Brownies',
              source: 'mine',
              calories: 320,
              protein: 5,
              carbs: 45,
              fat: 15,
              time: 45,
              servings: 12,
              keywords: ['Dessert', 'Chocolate', 'Easy'],
            },
          ] as RecipeSearchResult[]);
        }
      } finally {
        setIsLoading(false);
      }
    };

    // Debounce search
    const timeoutId = setTimeout(fetchRecipes, 300);
    return () => clearTimeout(timeoutId);
  }, [searchQuery, filters, currentPage, isInitialized]);

  const activeFilterCount = 
    (filters.sourceType !== 'all' ? 1 : 0) +
    filters.keywords.length +
    (filters.maxCalories !== 2000 ? 1 : 0) +
    (filters.minProtein > 0 ? 1 : 0) +
    (filters.maxCarbs !== 300 ? 1 : 0) +
    (filters.maxFat !== 100 ? 1 : 0);

  const removeFilter = (type: 'source' | 'keyword', value?: string) => {
    if (type === 'source') {
      setFilters({ ...filters, sourceType: 'all' });
    } else if (type === 'keyword' && value) {
      setFilters({ ...filters, keywords: filters.keywords.filter(k => k !== value) });
    }
  };

  const toggleFavorite = (id: string) => {
    setFavorites(prev => {
      const newFavorites = new Set(prev);
      if (newFavorites.has(id)) {
        newFavorites.delete(id);
      } else {
        newFavorites.add(id);
      }
      return newFavorites;
    });
  };

  const handleRecipeClick = async (recipe: RecipeSearchResult) => {
    try {
      // Fetch full recipe details from backend
      const fullRecipe = await getRecipeById(recipe.id);
      
      // Convert to detail format
      setSelectedRecipe({
        id: fullRecipe.id,
        name: fullRecipe.name,
        source: fullRecipe.source,
        calories: fullRecipe.calories,
        protein: fullRecipe.protein,
        carbs: fullRecipe.carbs,
        fat: fullRecipe.fat,
        fiber: fullRecipe.fiber,
        sugar: fullRecipe.sugar,
        saturated_fat: fullRecipe.saturated_fat,
        cholesterol: fullRecipe.cholesterol,
        sodium: fullRecipe.sodium,
        totalTime: fullRecipe.time,
        servings: fullRecipe.servings,
        keywords: fullRecipe.keywords || [],
        ingredients: fullRecipe.ingredients || [],
        steps: fullRecipe.steps || [],
      });
    } catch (error) {
      console.error('Failed to fetch recipe details:', error);
      // Fallback to basic info
      setSelectedRecipe({
        id: recipe.id,
        name: recipe.name,
        source: recipe.source,
        calories: recipe.calories,
        protein: recipe.protein,
        carbs: recipe.carbs,
        fat: recipe.fat,
        fiber: recipe.fiber,
        sugar: recipe.sugar,
        saturated_fat: recipe.saturated_fat,
        cholesterol: recipe.cholesterol,
        sodium: recipe.sodium,
        totalTime: recipe.time,
        servings: recipe.servings,
        keywords: recipe.keywords,
        ingredients: [],
        steps: [],
      });
    }
  };

  return (
    <div className="min-h-screen bg-gray-50 p-4 md:p-8">
      <div className="max-w-7xl mx-auto">
        {/* Header */}
        <div className="mb-6">
          <h1 className="text-3xl font-bold text-gray-900 mb-2">Recipe Explorer</h1>
          <p className="text-gray-600">Discover and save your favorite recipes</p>
        </div>

        {/* Search & Filter Bar */}
        <div className="bg-white rounded-lg border border-gray-200 p-4 mb-6">
          <div className="flex gap-4 items-center">
            <div className="flex-1 relative">
              <Search className="absolute left-3 top-1/2 -translate-y-1/2 text-gray-500" size={20} />
              <input
                type="text"
                placeholder="Search by name, ingredient, or cuisine..."
                value={searchQuery}
                onChange={(e) => setSearchQuery(e.target.value)}
                className="w-full pl-10 pr-4 py-2 border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-emerald-500 focus:border-transparent text-gray-900 placeholder-gray-500"
              />
            </div>
            <button 
              onClick={() => setIsFilterOpen(!isFilterOpen)}
              className="flex items-center gap-2 px-4 py-2 border border-gray-300 rounded-lg hover:bg-gray-50 transition-colors relative text-gray-800"
            >
              <Filter size={20} />
              <span className="hidden sm:inline">Filters</span>
              {activeFilterCount > 0 && (
                <span className="absolute -top-2 -right-2 w-5 h-5 bg-emerald-600 text-white text-xs rounded-full flex items-center justify-center">
                  {activeFilterCount}
                </span>
              )}
            </button>
            <div className="flex gap-1 border border-gray-300 rounded-lg overflow-hidden">
              <button
                onClick={() => setViewMode('grid')}
                className={`p-2 ${viewMode === 'grid' ? 'bg-emerald-50 text-emerald-600' : 'text-gray-800 hover:bg-gray-50'}`}
              >
                <Grid3x3 size={20} />
              </button>
              <button
                onClick={() => setViewMode('list')}
                className={`p-2 ${viewMode === 'list' ? 'bg-emerald-50 text-emerald-600' : 'text-gray-800 hover:bg-gray-50'}`}
              >
                <List size={20} />
              </button>
            </div>
          </div>

          {/* Active Filter Chips */}
          {activeFilterCount > 0 && (
            <div className="flex gap-2 mt-4 flex-wrap">
              {filters.sourceType !== 'all' && (
                <span className="px-3 py-1 bg-blue-50 text-blue-700 rounded-full text-sm font-medium flex items-center gap-2">
                  {filters.sourceType === 'dataset' ? 'Dataset' : 'My'} Recipes
                  <button onClick={() => removeFilter('source')} className="hover:bg-blue-100 rounded-full">
                    <X size={14} />
                  </button>
                </span>
              )}
              {filters.keywords.map(keyword => (
                <span key={keyword} className="px-3 py-1 bg-purple-50 text-purple-700 rounded-full text-sm font-medium flex items-center gap-2">
                  {keyword}
                  <button onClick={() => removeFilter('keyword', keyword)} className="hover:bg-purple-100 rounded-full">
                    <X size={14} />
                  </button>
                </span>
              ))}
            </div>
          )}
        </div>

        {/* Filter Panel & Recipe Grid */}
        <div className="flex gap-6">
          {/* Desktop Filter Panel */}
          <div className="hidden lg:block">
            {isFilterOpen && (
              <FilterPanel
                isOpen={isFilterOpen}
                onClose={() => setIsFilterOpen(false)}
                filters={filters}
                onFiltersChange={setFilters}
              />
            )}
          </div>

          {/* Mobile Filter Panel */}
          <div className="lg:hidden">
            <FilterPanel
              isOpen={isFilterOpen}
              onClose={() => setIsFilterOpen(false)}
              filters={filters}
              onFiltersChange={setFilters}
            />
          </div>

          {/* Recipe Grid/List */}
          <div className="flex-1">
            {isLoading && recipes.length === 0 ? (
              <div className="flex items-center justify-center h-64">
                <div className="text-gray-500">Loading recipes...</div>
              </div>
            ) : recipes.length === 0 ? (
              <div className="flex flex-col items-center justify-center h-64 text-gray-500">
                <div className="text-4xl mb-4">🔍</div>
                <div className="text-lg font-semibold mb-2">No recipes found</div>
                <div className="text-sm">Try adjusting your filters or search terms</div>
              </div>
            ) : viewMode === 'grid' ? (
              <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-6">
                {recipes.map((recipe) => (
                  <RecipeCard
                    key={recipe.id}
                    recipe={recipe}
                    onClick={() => handleRecipeClick(recipe)}
                    onFavorite={toggleFavorite}
                    onAddToMenu={(id) => console.log('Add to menu:', id)}
                    onShare={(id) => console.log('Share:', id)}
                    isFavorited={favorites.has(recipe.id)}
                  />
                ))}
              </div>
            ) : (
              <div className="space-y-4">
                {recipes.map((recipe) => (
                  <RecipeCard
                    key={recipe.id}
                    recipe={recipe}
                    onClick={() => handleRecipeClick(recipe)}
                    onFavorite={toggleFavorite}
                    onAddToMenu={(id) => console.log('Add to menu:', id)}
                    onShare={(id) => console.log('Share:', id)}
                    isFavorited={favorites.has(recipe.id)}
                  />
                ))}
              </div>
            )}
          </div>
        </div>

        {/* Pagination Controls */}
        {totalRecipes > 0 && (
          <div className="flex items-center justify-between px-4 py-6 border-t border-gray-200">
            <button
              onClick={() => setCurrentPage(p => Math.max(1, p - 1))}
              disabled={currentPage === 1}
              className="flex items-center gap-2 px-4 py-2 text-sm font-medium text-gray-900 bg-white border border-gray-300 rounded-lg hover:bg-gray-50 disabled:opacity-50 disabled:cursor-not-allowed"
            >
              <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M15 19l-7-7 7-7" />
              </svg>
              Previous
            </button>
            
            <div className="text-sm text-gray-900">
              Page <span className="font-medium">{currentPage}</span> of{' '}
              <span className="font-medium">{Math.ceil(totalRecipes / recipesPerPage)}</span>
              {' '}({totalRecipes} recipes)
            </div>
            
            <button
              onClick={() => setCurrentPage(p => Math.min(Math.ceil(totalRecipes / recipesPerPage), p + 1))}
              disabled={currentPage >= Math.ceil(totalRecipes / recipesPerPage)}
              className="flex items-center gap-2 px-4 py-2 text-sm font-medium text-gray-900 bg-white border border-gray-300 rounded-lg hover:bg-gray-50 disabled:opacity-50 disabled:cursor-not-allowed"
            >
              Next
              <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 5l7 7-7 7" />
              </svg>
            </button>
          </div>
        )}
      </div>

      {/* Recipe Detail Modal */}
      {selectedRecipe && (
        <RecipeDetailModal
          recipe={selectedRecipe}
          isOpen={!!selectedRecipe}
          onClose={() => setSelectedRecipe(null)}
          onFavorite={() => toggleFavorite(selectedRecipe.id)}
          onAddToMenu={() => console.log('Add to menu:', selectedRecipe.id)}
          onShare={() => console.log('Share:', selectedRecipe.id)}
          isFavorited={favorites.has(selectedRecipe.id)}
        />
      )}
    </div>
  );
}
