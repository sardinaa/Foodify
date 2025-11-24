'use client';

import { useState, useEffect } from 'react';
import { Calendar, Plus, ShoppingCart, Settings, X, Trash2, ChefHat } from 'lucide-react';
import { DndContext, DragOverlay, closestCenter, PointerSensor, useSensor, useSensors } from '@dnd-kit/core';
import { searchRecipes, getRecipeById } from '@/lib/apiClient';
import RecipeDetailModal from '@/components/RecipeDetailModal';
import { formatTime } from '@/lib/utils';

interface MealSlot {
  day: string;
  meal: string;
  recipe?: {
    id: string;
    name: string;
    calories: number;
    protein: number;
    carbs: number;
    fat: number;
    time: number;
    image?: string;
  };
}

export default function HomePage() {
  const daysOfWeek = ['Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday', 'Saturday', 'Sunday'];
  const mealTypes = ['Breakfast', 'Lunch', 'Dinner'];
  
  const [mealPlan, setMealPlan] = useState<Record<string, MealSlot>>({});
  const [activeId, setActiveId] = useState<string | null>(null);
  const [showRecipeSearch, setShowRecipeSearch] = useState(false);
  const [selectedSlot, setSelectedSlot] = useState<{ day: string; meal: string } | null>(null);
  const [searchQuery, setSearchQuery] = useState('');
  const [searchResults, setSearchResults] = useState<any[]>([]);
  const [isSearching, setIsSearching] = useState(false);
  const [showShoppingList, setShowShoppingList] = useState(false);
  const [selectedRecipe, setSelectedRecipe] = useState<any>(null);
  const [favorites, setFavorites] = useState<Set<string>>(new Set());
  
  const sensors = useSensors(
    useSensor(PointerSensor, {
      activationConstraint: {
        distance: 8,
      },
    })
  );
  
  // Load meal plan from localStorage on mount
  useEffect(() => {
    const saved = localStorage.getItem('mealPlan');
    if (saved) {
      try {
        const parsed = JSON.parse(saved);
        // Check if any recipe is missing the time field - if so, clear old data
        const hasOldData = Object.values(parsed).some((slot: any) => 
          slot.recipe && slot.recipe.time === undefined
        );
        if (hasOldData) {
          console.log('Clearing old meal plan data (missing time field)');
          localStorage.removeItem('mealPlan');
        } else {
          setMealPlan(parsed);
        }
      } catch (error) {
        console.error('Failed to load meal plan:', error);
      }
    }
  }, []);
  
  // Save meal plan to localStorage whenever it changes
  useEffect(() => {
    if (Object.keys(mealPlan).length > 0) {
      localStorage.setItem('mealPlan', JSON.stringify(mealPlan));
    }
  }, [mealPlan]);
  
  // Search recipes
  useEffect(() => {
    const timer = setTimeout(async () => {
      if (searchQuery.trim()) {
        setIsSearching(true);
        try {
          const result = await searchRecipes({ search: searchQuery, limit: 20 });
          setSearchResults(result.recipes);
        } catch (error) {
          console.error('Search failed:', error);
        }
        setIsSearching(false);
      } else {
        setSearchResults([]);
      }
    }, 300);
    
    return () => clearTimeout(timer);
  }, [searchQuery]);
  
  // Add recipe to meal slot
  const addRecipeToSlot = (day: string, meal: string, recipe: any) => {
    const key = `${day}-${meal}`;
    setMealPlan(prev => ({
      ...prev,
      [key]: { day, meal, recipe }
    }));
    setShowRecipeSearch(false);
    setSelectedSlot(null);
    setSearchQuery('');
  };
  
  // Remove recipe from slot
  const removeRecipe = (day: string, meal: string) => {
    const key = `${day}-${meal}`;
    setMealPlan(prev => {
      const newPlan = { ...prev };
      delete newPlan[key];
      return newPlan;
    });
  };
  
  // Open recipe search modal
  const openRecipeSearch = (day: string, meal: string) => {
    setSelectedSlot({ day, meal });
    setShowRecipeSearch(true);
  };
  
  // View recipe details
  const handleRecipeClick = async (recipeId: string) => {
    try {
      const fullRecipe = await getRecipeById(recipeId);
      setSelectedRecipe({
        id: fullRecipe.id,
        name: fullRecipe.name,
        category: fullRecipe.category,
        source: fullRecipe.source || 'dataset',
        description: fullRecipe.description || '',
        ingredients: fullRecipe.ingredients || [],
        steps: fullRecipe.steps || [],
        servings: fullRecipe.servings || 4,
        calories: fullRecipe.calories || 0,
        protein: fullRecipe.protein || 0,
        carbs: fullRecipe.carbs || 0,
        fat: fullRecipe.fat || 0,
        fiber: fullRecipe.fiber,
        sugar: fullRecipe.sugar,
        saturated_fat: fullRecipe.saturated_fat,
        cholesterol: fullRecipe.cholesterol,
        sodium: fullRecipe.sodium,
        time: fullRecipe.time || 30,
        keywords: fullRecipe.keywords || [],
      });
    } catch (error) {
      console.error('Failed to fetch recipe details:', error);
    }
  };
  
  // Toggle favorite
  const toggleFavorite = (recipeId: string) => {
    setFavorites(prev => {
      const newFavorites = new Set(prev);
      if (newFavorites.has(recipeId)) {
        newFavorites.delete(recipeId);
      } else {
        newFavorites.add(recipeId);
      }
      return newFavorites;
    });
  };
  
  // Calculate weekly nutrition totals
  const calculateNutrition = () => {
    const meals = Object.values(mealPlan);
    return meals.reduce((acc, slot) => {
      if (slot.recipe) {
        acc.calories += slot.recipe.calories || 0;
        acc.protein += slot.recipe.protein || 0;
        acc.carbs += slot.recipe.carbs || 0;
        acc.fat += slot.recipe.fat || 0;
      }
      return acc;
    }, { calories: 0, protein: 0, carbs: 0, fat: 0 });
  };
  
  const weeklyNutrition = calculateNutrition();
  const dailyAverage = {
    calories: Math.round(weeklyNutrition.calories / 7),
    protein: Math.round(weeklyNutrition.protein / 7),
    carbs: Math.round(weeklyNutrition.carbs / 7),
    fat: Math.round(weeklyNutrition.fat / 7),
  };

  return (
    <div className="min-h-screen bg-gray-50 p-4 md:p-8">
      {/* Header */}
      <div className="max-w-7xl mx-auto mb-8">
        <div className="flex items-center justify-between mb-4">
          <div>
            <h1 className="text-3xl font-bold text-gray-900">Weekly Menu</h1>
            <p className="text-gray-600 mt-1">Plan your meals for the week</p>
          </div>
          <div className="flex gap-2">
            <button 
              onClick={() => setShowShoppingList(true)}
              className="flex items-center gap-2 px-4 py-2 bg-white border border-gray-200 rounded-lg hover:bg-gray-50 transition-colors"
            >
              <ShoppingCart size={20} />
              <span className="hidden sm:inline">Shopping List</span>
            </button>
          </div>
        </div>

        {/* Nutritional Dashboard */}
        <div className="grid grid-cols-1 md:grid-cols-4 gap-4 mb-8">
          <div className="bg-white rounded-lg p-4 border border-gray-200">
            <div className="text-sm text-gray-600 mb-1">Daily Avg Calories</div>
            <div className="text-2xl font-bold text-gray-900">{dailyAverage.calories}</div>
            <div className="text-xs text-gray-500">Weekly: {weeklyNutrition.calories}</div>
          </div>
          <div className="bg-white rounded-lg p-4 border border-gray-200">
            <div className="text-sm text-gray-600 mb-1">Daily Avg Protein</div>
            <div className="text-2xl font-bold text-gray-900">{dailyAverage.protein}g</div>
            <div className="text-xs text-gray-500">Weekly: {weeklyNutrition.protein}g</div>
          </div>
          <div className="bg-white rounded-lg p-4 border border-gray-200">
            <div className="text-sm text-gray-600 mb-1">Daily Avg Carbs</div>
            <div className="text-2xl font-bold text-gray-900">{dailyAverage.carbs}g</div>
            <div className="text-xs text-gray-500">Weekly: {weeklyNutrition.carbs}g</div>
          </div>
          <div className="bg-white rounded-lg p-4 border border-gray-200">
            <div className="text-sm text-gray-600 mb-1">Daily Avg Fat</div>
            <div className="text-2xl font-bold text-gray-900">{dailyAverage.fat}g</div>
            <div className="text-xs text-gray-500">Weekly: {weeklyNutrition.fat}g</div>
          </div>
        </div>

        {/* Weekly Calendar */}
        <div className="bg-white rounded-lg border border-gray-200 overflow-hidden">
          <div className="overflow-x-auto">
            <table className="w-full">
              <thead className="bg-gray-50 border-b border-gray-200">
                <tr>
                  <th className="px-4 py-3 text-left text-sm font-semibold text-gray-900 w-32">Meal</th>
                  {daysOfWeek.map((day) => (
                    <th key={day} className="px-4 py-3 text-left text-sm font-semibold text-gray-900 min-w-[180px]">
                      {day}
                    </th>
                  ))}
                </tr>
              </thead>
              <tbody className="divide-y divide-gray-200">
                {mealTypes.map((meal) => (
                  <tr key={meal}>
                    <td className="px-4 py-4 text-sm font-medium text-gray-900 bg-gray-50">
                      {meal}
                    </td>
                    {daysOfWeek.map((day) => {
                      const key = `${day}-${meal}`;
                      const slot = mealPlan[key];
                      
                      return (
                        <td key={key} className="px-4 py-4">
                          {slot?.recipe ? (
                            <div className="relative h-32 bg-linear-to-br from-white to-gray-50 border-2 border-gray-200 rounded-xl p-4 hover:shadow-lg hover:border-emerald-400 transition-all duration-200 group">
                              <button
                                onClick={(e) => {
                                  e.stopPropagation();
                                  removeRecipe(day, meal);
                                }}
                                className="absolute -top-2 -right-2 bg-red-500 text-white rounded-full p-1.5 opacity-0 group-hover:opacity-100 transition-opacity shadow-md hover:bg-red-600 z-10"
                              >
                                <X size={12} />
                              </button>
                              <button
                                onClick={() => slot.recipe && handleRecipeClick(slot.recipe.id)}
                                className="text-left w-full h-full flex flex-col justify-between overflow-hidden"
                              >
                                <div>
                                  <div className="text-sm font-semibold text-gray-900 mb-2 line-clamp-2 leading-tight min-h-10">
                                    {slot.recipe.name}
                                  </div>
                                  <div className="flex items-center gap-2 text-xs text-gray-600 mb-2">
                                    <span className="flex items-center gap-1 whitespace-nowrap">
                                      <span className="w-1.5 h-1.5 bg-emerald-500 rounded-full"></span>
                                      {slot.recipe.calories || 0} cal
                                    </span>
                                    <span className="text-gray-400">•</span>
                                    <span className="flex items-center gap-1 whitespace-nowrap">
                                      <span className="w-1.5 h-1.5 bg-orange-500 rounded-full"></span>
                                      {formatTime(slot.recipe.time || 0)}
                                    </span>
                                  </div>
                                </div>
                                <div className="flex gap-1 mt-auto flex-wrap">
                                  <span className="px-1.5 py-0.5 bg-blue-50 text-blue-700 rounded text-[10px] font-medium whitespace-nowrap">
                                    P {Math.round(slot.recipe.protein || 0)}g
                                  </span>
                                  <span className="px-1.5 py-0.5 bg-orange-50 text-orange-700 rounded text-[10px] font-medium whitespace-nowrap">
                                    C {Math.round(slot.recipe.carbs || 0)}g
                                  </span>
                                  <span className="px-1.5 py-0.5 bg-purple-50 text-purple-700 rounded text-[10px] font-medium whitespace-nowrap">
                                    F {Math.round(slot.recipe.fat || 0)}g
                                  </span>
                                </div>
                              </button>
                            </div>
                          ) : (
                            <button
                              onClick={() => openRecipeSearch(day, meal)}
                              className="flex flex-col items-center justify-center w-full h-32 border-2 border-dashed border-gray-300 rounded-xl hover:border-emerald-500 hover:bg-emerald-50 cursor-pointer transition-all duration-200 group"
                            >
                              <Plus size={24} className="text-gray-400 group-hover:text-emerald-600 mb-1" />
                              <span className="text-xs text-gray-500 group-hover:text-emerald-600">Add Recipe</span>
                            </button>
                          )}
                        </td>
                      );
                    })}
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>
      </div>

      {/* Recipe Search Modal */}
      {showRecipeSearch && selectedSlot && (
        <div className="fixed inset-0 bg-black/50 flex items-center justify-center z-50 p-4">
          <div className="bg-white rounded-lg max-w-2xl w-full max-h-[80vh] flex flex-col">
            <div className="flex items-center justify-between p-6 border-b border-gray-200">
              <div>
                <h2 className="text-xl font-bold text-gray-900">Add Recipe</h2>
                <p className="text-sm text-gray-600 mt-1">
                  {selectedSlot.day} - {selectedSlot.meal}
                </p>
              </div>
              <button
                onClick={() => {
                  setShowRecipeSearch(false);
                  setSelectedSlot(null);
                  setSearchQuery('');
                }}
                className="p-2 hover:bg-gray-100 rounded-lg"
              >
                <X size={20} />
              </button>
            </div>
            
            <div className="p-6 border-b border-gray-200">
              <input
                type="text"
                placeholder="Search recipes..."
                value={searchQuery}
                onChange={(e) => setSearchQuery(e.target.value)}
                className="w-full px-4 py-2 border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-emerald-500"
                autoFocus
              />
            </div>
            
            <div className="flex-1 overflow-y-auto p-6">
              {isSearching ? (
                <div className="flex items-center justify-center h-32">
                  <div className="text-gray-500">Searching...</div>
                </div>
              ) : searchResults.length > 0 ? (
                <div className="space-y-3">
                  {searchResults.map((recipe) => (
                    <button
                      key={recipe.id}
                      onClick={() => addRecipeToSlot(selectedSlot.day, selectedSlot.meal, recipe)}
                      className="w-full text-left bg-white border border-gray-200 rounded-lg p-4 hover:border-emerald-500 hover:bg-emerald-50 transition-colors"
                    >
                      <div className="font-medium text-gray-900 mb-2">{recipe.name}</div>
                      <div className="flex gap-4 text-sm text-gray-600">
                        <span>{recipe.calories} cal</span>
                        <span>{formatTime(recipe.time)}</span>
                        <span className="text-blue-600">P: {recipe.protein}g</span>
                        <span className="text-orange-600">C: {recipe.carbs}g</span>
                        <span className="text-purple-600">F: {recipe.fat}g</span>
                      </div>
                    </button>
                  ))}
                </div>
              ) : searchQuery ? (
                <div className="flex flex-col items-center justify-center h-32 text-gray-500">
                  <ChefHat size={32} className="mb-2" />
                  <div>No recipes found</div>
                </div>
              ) : (
                <div className="flex flex-col items-center justify-center h-32 text-gray-500">
                  <ChefHat size={32} className="mb-2" />
                  <div>Start typing to search recipes</div>
                </div>
              )}
            </div>
          </div>
        </div>
      )}

      {/* Shopping List Modal */}
      {showShoppingList && (
        <div className="fixed inset-0 bg-black/50 flex items-center justify-center z-50 p-4">
          <div className="bg-white rounded-lg max-w-2xl w-full max-h-[80vh] flex flex-col">
            <div className="flex items-center justify-between p-6 border-b border-gray-200">
              <h2 className="text-xl font-bold text-gray-900">Shopping List</h2>
              <button
                onClick={() => setShowShoppingList(false)}
                className="p-2 hover:bg-gray-100 rounded-lg"
              >
                <X size={20} />
              </button>
            </div>
            
            <div className="flex-1 overflow-y-auto p-6">
              {Object.values(mealPlan).length > 0 ? (
                <div className="space-y-4">
                  <div className="text-sm text-gray-600 mb-4">
                    Ingredients needed for {Object.values(mealPlan).length} planned meals
                  </div>
                  {Object.values(mealPlan).map((slot, index) => (
                    slot.recipe && (
                      <div key={index} className="border-b border-gray-200 pb-3">
                        <div className="font-medium text-gray-900">{slot.recipe.name}</div>
                        <div className="text-sm text-gray-600">{slot.day} - {slot.meal}</div>
                      </div>
                    )
                  ))}
                  <div className="mt-6 p-4 bg-blue-50 rounded-lg">
                    <div className="text-sm text-blue-900">
                      💡 Detailed shopping list with quantities coming soon!
                    </div>
                  </div>
                </div>
              ) : (
                <div className="flex flex-col items-center justify-center h-32 text-gray-500">
                  <ShoppingCart size={32} className="mb-2" />
                  <div>Add recipes to your meal plan to generate a shopping list</div>
                </div>
              )}
            </div>
          </div>
        </div>
      )}

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
