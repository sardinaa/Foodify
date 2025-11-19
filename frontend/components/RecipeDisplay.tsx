'use client';

import { Recipe, NutritionSummary } from '@/lib/apiClient';

interface RecipeDisplayProps {
  recipe: Recipe;
  nutrition: NutritionSummary;
  tags: string[];
}

export default function RecipeDisplay({ recipe, nutrition, tags }: RecipeDisplayProps) {
  return (
    <div className="bg-white rounded-lg shadow-md p-6 space-y-6">
      {/* Header */}
      <div>
        <h2 className="text-3xl font-bold text-gray-800 mb-2">{recipe.name}</h2>
        {recipe.description && (
          <p className="text-gray-600">{recipe.description}</p>
        )}
        <div className="flex gap-4 mt-3 text-sm text-gray-600">
          <span>⏱️ {recipe.total_time_minutes} minutes</span>
          <span>🍽️ {recipe.servings} servings</span>
        </div>
      </div>

      {/* Tags */}
      {tags.length > 0 && (
        <div className="flex flex-wrap gap-2">
          {tags.map((tag, idx) => (
            <span
              key={idx}
              className="px-3 py-1 bg-orange-100 text-orange-700 rounded-full text-sm font-medium"
            >
              {tag}
            </span>
          ))}
        </div>
      )}

      {/* Nutrition */}
      <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
        <div className="bg-gray-50 rounded-lg p-4 text-center">
          <p className="text-2xl font-bold text-orange-600">
            {nutrition.per_serving.kcal}
          </p>
          <p className="text-sm text-gray-600">Calories</p>
        </div>
        <div className="bg-gray-50 rounded-lg p-4 text-center">
          <p className="text-2xl font-bold text-blue-600">
            {nutrition.per_serving.protein}g
          </p>
          <p className="text-sm text-gray-600">Protein</p>
        </div>
        <div className="bg-gray-50 rounded-lg p-4 text-center">
          <p className="text-2xl font-bold text-green-600">
            {nutrition.per_serving.carbs}g
          </p>
          <p className="text-sm text-gray-600">Carbs</p>
        </div>
        <div className="bg-gray-50 rounded-lg p-4 text-center">
          <p className="text-2xl font-bold text-yellow-600">
            {nutrition.per_serving.fat}g
          </p>
          <p className="text-sm text-gray-600">Fat</p>
        </div>
      </div>

      {/* Ingredients */}
      <div>
        <h3 className="text-xl font-semibold mb-3">Ingredients</h3>
        <ul className="space-y-2">
          {recipe.ingredients.map((ingredient, idx) => (
            <li key={idx} className="flex items-center">
              <span className="w-2 h-2 bg-orange-500 rounded-full mr-3"></span>
              <span>
                {ingredient.quantity} {ingredient.unit} {ingredient.name}
              </span>
            </li>
          ))}
        </ul>
      </div>

      {/* Steps */}
      <div>
        <h3 className="text-xl font-semibold mb-3">Instructions</h3>
        <ol className="space-y-3">
          {recipe.steps.map((step, idx) => (
            <li key={idx} className="flex">
              <span className="shrink-0 w-8 h-8 bg-orange-500 text-white rounded-full flex items-center justify-center font-semibold mr-3">
                {step.step_number}
              </span>
              <p className="flex-1 pt-1">{step.instruction}</p>
            </li>
          ))}
        </ol>
      </div>

      {/* Total Nutrition */}
      <div className="bg-gray-50 rounded-lg p-4">
        <h4 className="font-semibold mb-2">Total Recipe Nutrition</h4>
        <div className="grid grid-cols-4 gap-2 text-sm text-gray-600">
          <div>
            <span className="font-medium">{nutrition.total.kcal}</span> kcal
          </div>
          <div>
            <span className="font-medium">{nutrition.total.protein}g</span> protein
          </div>
          <div>
            <span className="font-medium">{nutrition.total.carbs}g</span> carbs
          </div>
          <div>
            <span className="font-medium">{nutrition.total.fat}g</span> fat
          </div>
        </div>
      </div>
    </div>
  );
}
