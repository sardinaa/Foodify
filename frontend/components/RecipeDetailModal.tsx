'use client';

import { X, Clock, Users, Heart, Plus, Share2, Printer, ChevronLeft, ChevronRight } from 'lucide-react';
import { useState } from 'react';
import { formatTime } from '@/lib/utils';

interface RecipeDetailProps {
  id: string;
  name: string;
  category: string;
  source: 'dataset' | 'mine';
  description?: string;
  image?: string;
  calories: number;
  protein: number;
  carbs: number;
  fat: number;
  prepTime?: number;
  cookTime?: number;
  totalTime?: number;
  servings: number;
  difficulty?: string;
  keywords: string[];
  ingredients: Array<{ name: string; quantity?: string; unit?: string }>;
  steps: Array<{ number: number; instruction: string }>;
}

interface RecipeDetailModalProps {
  recipe: RecipeDetailProps;
  isOpen: boolean;
  onClose: () => void;
  onFavorite?: () => void;
  onAddToMenu?: () => void;
  onShare?: () => void;
  isFavorited?: boolean;
  similarRecipes?: RecipeDetailProps[];
}

export default function RecipeDetailModal({
  recipe,
  isOpen,
  onClose,
  onFavorite,
  onAddToMenu,
  onShare,
  isFavorited = false,
  similarRecipes = [],
}: RecipeDetailModalProps) {
  const [servings, setServings] = useState(recipe.servings);
  const [ingredientsExpanded, setIngredientsExpanded] = useState(true);
  const [instructionsExpanded, setInstructionsExpanded] = useState(true);
  const [nutritionExpanded, setNutritionExpanded] = useState(true);

  const servingMultiplier = servings / recipe.servings;

  const adjustQuantity = (quantity?: string) => {
    if (!quantity) return '';
    const num = parseFloat(quantity);
    if (isNaN(num)) return quantity;
    return (num * servingMultiplier).toFixed(1);
  };

  if (!isOpen) return null;

  return (
    <div className="fixed inset-0 z-50 overflow-hidden">
      {/* Backdrop */}
      <div
        className="absolute inset-0 bg-black/60"
        onClick={onClose}
      />

      {/* Modal */}
      <div className="absolute inset-0 md:inset-4 lg:inset-8 bg-white rounded-none md:rounded-lg overflow-hidden flex flex-col">
        {/* Header */}
        <div className="flex items-center justify-between px-6 py-4 border-b border-gray-200 bg-white sticky top-0 z-10">
          <h2 className="text-2xl font-bold text-gray-900 flex-1 mr-4">{recipe.name}</h2>
          <button
            onClick={onClose}
            className="p-2 hover:bg-gray-100 rounded-lg transition-colors"
          >
            <X size={24} />
          </button>
        </div>

        {/* Content */}
        <div className="flex-1 overflow-y-auto">
          <div className="max-w-4xl mx-auto p-6">
            {/* Image and Badges */}
            <div className="mb-6">
              <div className="relative h-64 md:h-96 bg-linear-to-br from-emerald-100 to-blue-100 rounded-lg overflow-hidden mb-4">
                {recipe.image ? (
                  <img
                    src={recipe.image}
                    alt={recipe.name}
                    className="w-full h-full object-cover"
                  />
                ) : (
                  <div className="flex items-center justify-center h-full text-gray-400">
                    <div className="text-center">
                      <div className="text-6xl mb-2">🍽️</div>
                      <div>No image available</div>
                    </div>
                  </div>
                )}
              </div>

              <div className="flex items-center gap-2 flex-wrap mb-4">
                <span
                  className={`px-3 py-1 rounded-full text-sm font-medium ${
                    recipe.source === 'dataset'
                      ? 'bg-blue-50 text-blue-700'
                      : 'bg-emerald-50 text-emerald-700'
                  }`}
                >
                  {recipe.source === 'dataset' ? 'Dataset Recipe' : 'My Recipe'}
                </span>
                <span className="px-3 py-1 bg-gray-100 text-gray-700 rounded-full text-sm font-medium">
                  {recipe.category}
                </span>
                {recipe.keywords && recipe.keywords.slice(0, 5).map((keyword) => (
                  <span
                    key={keyword}
                    className="px-3 py-1 bg-gray-50 text-gray-600 rounded-full text-sm"
                  >
                    {keyword}
                  </span>
                ))}
              </div>

              {recipe.description && (
                <p className="text-gray-700 mb-4">{recipe.description}</p>
              )}
            </div>

            {/* Info Bar */}
            <div className="grid grid-cols-2 md:grid-cols-4 gap-4 mb-6 p-4 bg-gray-50 rounded-lg">
              {recipe.totalTime && (
                <div>
                  <div className="text-xs text-gray-600 mb-1">Total Time</div>
                  <div className="flex items-center gap-2">
                    <Clock size={20} className="text-gray-400" />
                    <span className="font-semibold text-gray-900">{formatTime(recipe.totalTime)}</span>
                  </div>
                </div>
              )}
              {recipe.prepTime && (
                <div>
                  <div className="text-xs text-gray-600 mb-1">Prep Time</div>
                  <div className="font-semibold text-gray-900">{formatTime(recipe.prepTime)}</div>
                </div>
              )}
              {recipe.cookTime && (
                <div>
                  <div className="text-xs text-gray-600 mb-1">Cook Time</div>
                  <div className="font-semibold text-gray-900">{formatTime(recipe.cookTime)}</div>
                </div>
              )}
              <div>
                <div className="text-xs text-gray-600 mb-1">Servings</div>
                <div className="flex items-center gap-2">
                  <button
                    onClick={() => setServings(Math.max(1, servings - 1))}
                    className="w-8 h-8 flex items-center justify-center bg-white border border-gray-300 rounded hover:bg-gray-50"
                  >
                    -
                  </button>
                  <span className="font-semibold text-gray-900 w-8 text-center">{servings}</span>
                  <button
                    onClick={() => setServings(servings + 1)}
                    className="w-8 h-8 flex items-center justify-center bg-white border border-gray-300 rounded hover:bg-gray-50"
                  >
                    +
                  </button>
                </div>
              </div>
            </div>

            {/* Ingredients Section */}
            <div className="mb-6">
              <button
                onClick={() => setIngredientsExpanded(!ingredientsExpanded)}
                className="flex items-center justify-between w-full mb-4"
              >
                <h3 className="text-xl font-bold text-gray-900">Ingredients</h3>
                <ChevronRight
                  size={20}
                  className={`transform transition-transform ${ingredientsExpanded ? 'rotate-90' : ''}`}
                />
              </button>

              {ingredientsExpanded && (
                <div className="space-y-2">
                  {recipe.ingredients && recipe.ingredients.length > 0 ? (
                    recipe.ingredients.map((ingredient, index) => (
                      <label key={index} className="flex items-start gap-3 p-2 hover:bg-gray-50 rounded cursor-pointer">
                        <input type="checkbox" className="mt-1" />
                        <span className="text-gray-900">
                          {ingredient.quantity && adjustQuantity(ingredient.quantity)}{' '}
                          {ingredient.unit}{' '}
                          {ingredient.name}
                        </span>
                      </label>
                    ))
                  ) : (
                    <p className="text-gray-500 text-center py-4">No ingredients available</p>
                  )}
                </div>
              )}
            </div>

            {/* Instructions Section */}
            <div className="mb-6">
              <button
                onClick={() => setInstructionsExpanded(!instructionsExpanded)}
                className="flex items-center justify-between w-full mb-4"
              >
                <h3 className="text-xl font-bold text-gray-900">Instructions</h3>
                <ChevronRight
                  size={20}
                  className={`transform transition-transform ${instructionsExpanded ? 'rotate-90' : ''}`}
                />
              </button>

              {instructionsExpanded && (
                <div className="space-y-4">
                  {recipe.steps && recipe.steps.length > 0 ? (
                    recipe.steps.map((step) => (
                      <div key={step.number} className="flex gap-4 p-4 bg-gray-50 rounded-lg">
                        <div className="shrink-0 w-8 h-8 bg-emerald-600 text-white rounded-full flex items-center justify-center font-semibold">
                          {step.number}
                        </div>
                        <p className="text-gray-900 flex-1">{step.instruction}</p>
                      </div>
                    ))
                  ) : (
                    <p className="text-gray-500 text-center py-4">No instructions available</p>
                  )}
                </div>
              )}
            </div>

            {/* Nutrition Panel */}
            <div className="mb-6">
              <button
                onClick={() => setNutritionExpanded(!nutritionExpanded)}
                className="flex items-center justify-between w-full mb-4"
              >
                <h3 className="text-xl font-bold text-gray-900">Nutrition (per serving)</h3>
                <ChevronRight
                  size={20}
                  className={`transform transition-transform ${nutritionExpanded ? 'rotate-90' : ''}`}
                />
              </button>

              {nutritionExpanded && (
                <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
                  <div className="p-4 bg-orange-50 rounded-lg">
                    <div className="text-sm text-orange-700 mb-1">Calories</div>
                    <div className="text-2xl font-bold text-orange-900">
                      {recipe.calories ? Math.round(recipe.calories) : 'N/A'}
                    </div>
                  </div>
                  <div className="p-4 bg-blue-50 rounded-lg">
                    <div className="text-sm text-blue-700 mb-1">Protein</div>
                    <div className="text-2xl font-bold text-blue-900">
                      {recipe.protein ? `${Math.round(recipe.protein)}g` : 'N/A'}
                    </div>
                  </div>
                  <div className="p-4 bg-amber-50 rounded-lg">
                    <div className="text-sm text-amber-700 mb-1">Carbs</div>
                    <div className="text-2xl font-bold text-amber-900">
                      {recipe.carbs ? `${Math.round(recipe.carbs)}g` : 'N/A'}
                    </div>
                  </div>
                  <div className="p-4 bg-purple-50 rounded-lg">
                    <div className="text-sm text-purple-700 mb-1">Fat</div>
                    <div className="text-2xl font-bold text-purple-900">
                      {recipe.fat ? `${Math.round(recipe.fat)}g` : 'N/A'}
                    </div>
                  </div>
                </div>
              )}
            </div>

            {/* Similar Recipes */}
            {similarRecipes.length > 0 && (
              <div className="mb-6">
                <h3 className="text-xl font-bold text-gray-900 mb-4">Similar Recipes</h3>
                <div className="flex gap-4 overflow-x-auto pb-2">
                  {similarRecipes.map((similar) => (
                    <div
                      key={similar.id}
                      className="flex-shrink-0 w-48 bg-white border border-gray-200 rounded-lg overflow-hidden cursor-pointer hover:shadow-md transition-shadow"
                    >
                      <div className="h-32 bg-linear-to-br from-emerald-100 to-blue-100" />
                      <div className="p-3">
                        <h4 className="font-semibold text-sm text-gray-900 line-clamp-2 mb-1">
                          {similar.name}
                        </h4>
                        <p className="text-xs text-gray-600">{Math.round(similar.calories)} cal</p>
                      </div>
                    </div>
                  ))}
                </div>
              </div>
            )}
          </div>
        </div>

        {/* Footer Actions */}
        <div className="px-6 py-4 border-t border-gray-200 bg-white flex items-center justify-between gap-4">
          <div className="flex gap-2">
            {onFavorite && (
              <button
                onClick={onFavorite}
                className={`flex items-center gap-2 px-4 py-2 rounded-lg transition-colors ${
                  isFavorited
                    ? 'bg-red-50 text-red-600 hover:bg-red-100'
                    : 'border border-gray-300 hover:bg-gray-50'
                }`}
              >
                <Heart size={18} fill={isFavorited ? 'currentColor' : 'none'} />
                <span className="hidden sm:inline">Favorite</span>
              </button>
            )}
            {onShare && (
              <button
                onClick={onShare}
                className="flex items-center gap-2 px-4 py-2 border border-gray-300 rounded-lg hover:bg-gray-50 transition-colors"
              >
                <Share2 size={18} />
                <span className="hidden sm:inline">Share</span>
              </button>
            )}
            <button
              onClick={() => window.print()}
              className="flex items-center gap-2 px-4 py-2 border border-gray-300 rounded-lg hover:bg-gray-50 transition-colors"
            >
              <Printer size={18} />
              <span className="hidden sm:inline">Print</span>
            </button>
          </div>

          {onAddToMenu && (
            <button
              onClick={onAddToMenu}
              className="flex items-center gap-2 px-6 py-2 bg-emerald-600 text-white rounded-lg hover:bg-emerald-700 transition-colors"
            >
              <Plus size={18} />
              Add to Menu
            </button>
          )}
        </div>
      </div>
    </div>
  );
}
