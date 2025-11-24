'use client';

import { Heart, Plus, Share2, Clock, Users, Flame } from 'lucide-react';
import { RecipeSearchResult } from '@/lib/apiClient';
import { formatTime } from '@/lib/utils';

interface RecipeCardProps {
  recipe: RecipeSearchResult;
  onClick: () => void;
  onFavorite?: (id: string) => void;
  onAddToMenu?: (id: string) => void;
  onShare?: (id: string) => void;
  isFavorited?: boolean;
}

export default function RecipeCard({
  recipe,
  onClick,
  onFavorite,
  onAddToMenu,
  onShare,
  isFavorited = false,
}: RecipeCardProps) {
  return (
    <div
      className="bg-white rounded-lg border border-gray-200 overflow-hidden hover:shadow-lg transition-shadow cursor-pointer group"
      onClick={onClick}
    >
      {/* Recipe Image */}
      <div className="relative h-48 bg-gradient-to-br from-emerald-100 to-blue-100 flex items-center justify-center">
        {recipe.image ? (
          <img
            src={recipe.image}
            alt={recipe.name}
            className="w-full h-full object-cover"
          />
        ) : (
          <div className="text-gray-400 text-center">
            <div className="text-4xl mb-2">🍽️</div>
            <div className="text-sm">No image available</div>
          </div>
        )}
        
        {/* View Recipe Overlay */}
        <div className="absolute inset-0 bg-black/60 opacity-0 group-hover:opacity-100 transition-opacity flex items-center justify-center">
          <span className="text-white font-semibold">View Recipe</span>
        </div>
      </div>

      {/* Recipe Info */}
      <div className="p-4">
        <div className="flex items-start justify-between mb-2">
          <h3 className="font-semibold text-gray-900 text-lg line-clamp-2 flex-1">
            {recipe.name}
          </h3>
          <span
            className={`px-2 py-1 rounded text-xs font-medium ml-2 flex-shrink-0 ${
              recipe.source === 'dataset'
                ? 'bg-blue-50 text-blue-700'
                : 'bg-emerald-50 text-emerald-700'
            }`}
          >
            {recipe.source === 'dataset' ? 'Dataset' : 'Mine'}
          </span>
        </div>

        <div className="flex items-center gap-2 mb-3 flex-wrap">
          {recipe.keywords.slice(0, 4).map((keyword) => (
            <span
              key={keyword}
              className="px-2 py-1 bg-gray-50 text-gray-600 rounded text-xs"
            >
              {keyword}
            </span>
          ))}
          {recipe.keywords.length > 4 && (
            <span className="px-2 py-1 bg-gray-50 text-gray-600 rounded text-xs">
              +{recipe.keywords.length - 4}
            </span>
          )}
        </div>

        {/* Stats */}
        <div className="flex items-center justify-between text-sm text-gray-600 mb-4 gap-3">
          <div className="flex items-center gap-1" title="Calories">
            <Flame size={16} className="text-orange-500" />
            <span>{Math.round(recipe.calories)}</span>
          </div>
          {recipe.time && (
            <div className="flex items-center gap-1" title="Time">
              <Clock size={16} className="text-gray-400" />
              <span>{formatTime(recipe.time)}</span>
            </div>
          )}
          <div className="flex items-center gap-1" title="Servings">
            <Users size={16} className="text-gray-400" />
            <span>{recipe.servings}</span>
          </div>
        </div>

        {/* Macros */}
        <div className="flex items-center gap-2 mb-4 pb-4 border-b border-gray-100">
          <span className="px-2 py-1 bg-blue-50 text-blue-700 rounded text-xs font-medium">
            P {Math.round(recipe.protein)}g
          </span>
          <span className="px-2 py-1 bg-orange-50 text-orange-700 rounded text-xs font-medium">
            C {Math.round(recipe.carbs)}g
          </span>
          <span className="px-2 py-1 bg-purple-50 text-purple-700 rounded text-xs font-medium">
            F {Math.round(recipe.fat)}g
          </span>
        </div>

        {/* Action Buttons */}
        <div className="flex items-center justify-end gap-2">
          {onFavorite && (
            <button
              onClick={(e) => {
                e.stopPropagation();
                onFavorite(recipe.id);
              }}
              className={`p-2 rounded-lg transition-colors ${
                isFavorited
                  ? 'bg-red-50 text-red-600 hover:bg-red-100'
                  : 'hover:bg-gray-100 text-gray-600'
              }`}
              title="Favorite"
            >
              <Heart size={18} fill={isFavorited ? 'currentColor' : 'none'} />
            </button>
          )}
          {onAddToMenu && (
            <button
              onClick={(e) => {
                e.stopPropagation();
                onAddToMenu(recipe.id);
              }}
              className="p-2 hover:bg-emerald-50 text-emerald-600 rounded-lg transition-colors"
              title="Add to Menu"
            >
              <Plus size={18} />
            </button>
          )}
          {onShare && (
            <button
              onClick={(e) => {
                e.stopPropagation();
                onShare(recipe.id);
              }}
              className="p-2 hover:bg-gray-100 text-gray-600 rounded-lg transition-colors"
              title="Share"
            >
              <Share2 size={18} />
            </button>
          )}
        </div>
      </div>
    </div>
  );
}
