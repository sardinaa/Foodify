'use client';

import { useState } from 'react';
import { Send, Camera, Image as ImageIcon, Link as LinkIcon, Loader2, X } from 'lucide-react';
import { sendChatMessage, getRecipeById, Recipe } from '@/lib/apiClient';
import type { RecipeSearchResult } from '@/lib/apiClient';
import { formatTime } from '@/lib/utils';
import RecipeDetailModal from '@/components/RecipeDetailModal';

type ChatRecipe = RecipeSearchResult & {
  fullRecipe?: Recipe; // Store the full recipe data from chat response
  dayName?: string; // For weekly menu organization
  mealType?: string; // breakfast, lunch, or dinner
  show_nutrition_only?: boolean; // Flag to show only nutrition info
};

type Message = {
  id: string;
  role: 'user' | 'assistant';
  content: string;
  timestamp: Date;
  recipes?: ChatRecipe[];
  isWeeklyMenu?: boolean; // Flag for weekly menu display
};

export default function ChatPage() {
  const [messages, setMessages] = useState<Message[]>([]);
  const [input, setInput] = useState('');
  const [isLoading, setIsLoading] = useState(false);
  const [sessionId] = useState(() => `session-${Date.now()}`);
  const [selectedRecipe, setSelectedRecipe] = useState<any>(null);
  const [showRecipeModal, setShowRecipeModal] = useState(false);
  const [selectedImage, setSelectedImage] = useState<File | null>(null);
  const [imagePreview, setImagePreview] = useState<string | null>(null);

  const starterPrompts = [
    'Find recipes with ingredients I have',
    'Scan a recipe photo',
    'Import recipe from URL',
    'Generate my weekly menu',
    'Show me high-protein meals',
    'Quick dinner ideas (<30 mins)',
  ];

  const handleImageSelect = (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0];
    if (file) {
      setSelectedImage(file);
      setImagePreview(URL.createObjectURL(file));
    }
  };

  const handleSend = async () => {
    if (!input.trim() && !selectedImage) return;

    const userMessage: Message = {
      id: Date.now().toString(),
      role: 'user',
      content: selectedImage ? `[Image uploaded] ${input || 'What can I make with this?'}` : input,
      timestamp: new Date(),
    };

    setMessages((prev) => [...prev, userMessage]);
    const userInput = input || (selectedImage ? 'Analyze this food image' : '');
    const imageToSend = selectedImage;
    setInput('');
    setSelectedImage(null);
    setImagePreview(null);
    setIsLoading(true);

    try {
      // Call backend chat API with optional image
      const response = await sendChatMessage(sessionId, userInput, imageToSend);
      
      // Convert Recipe objects to ChatRecipe format
      // For dataset recipes, we need to fetch nutrition data from /api/rag/search
      // For now, show what we have and fetch details on click
      const timestamp = Date.now();
      const recipeResults: ChatRecipe[] = await Promise.all(
        (response.suggested_recipes || []).map(async (recipe, index) => {
          // Use recipe ID first (for modified recipes), then source_ref (for dataset recipes)
          const recipeId = recipe.id?.toString() || recipe.source_ref;
          const uniqueId = (recipeId && recipeId !== '0') 
            ? recipeId 
            : `chat-recipe-${timestamp}-${index}`;
          
          // Check if recipe already has nutrition data (from image uploads or chat extraction)
          const hasNutritionData = recipe.calories !== undefined && recipe.calories !== null;
          
          // For dataset recipes (not modified), fetch the full metadata to get nutrition data
          // Skip modified recipes (ID starts with "modified_" or "session_") as they don't exist in the database
          // Skip recipes that already have nutrition data
          let nutritionData = { 
            calories: recipe.calories || 0, 
            protein: recipe.protein || 0, 
            carbs: recipe.carbs || 0, 
            fat: recipe.fat || 0 
          };
          const isModified = recipeId && (recipeId.startsWith('modified_') || recipeId.startsWith('session_'));
          if (recipeId && recipeId !== '0' && !isModified && !hasNutritionData) {
            try {
              const fullData = await getRecipeById(recipeId, sessionId);
              nutritionData = {
                calories: fullData.calories || 0,
                protein: fullData.protein || 0,
                carbs: fullData.carbs || 0,
                fat: fullData.fat || 0,
              };
            } catch (error) {
              console.log('Could not fetch nutrition data for recipe', recipeId);
            }
          }
          
          return {
            id: uniqueId,
            name: recipe.name,
            category: recipe.tags?.[0] || 'Other',
            source: (recipe.source_type as 'dataset' | 'mine') || 'dataset',
            calories: nutritionData.calories,
            protein: nutritionData.protein,
            carbs: nutritionData.carbs,
            fat: nutritionData.fat,
            time: recipe.total_time_minutes,
            servings: recipe.servings,
            keywords: recipe.tags || [],
            fullRecipe: recipe, // Store the complete recipe data (though ingredients/steps will be empty)
            dayName: (recipe as any).day_name, // For weekly menu
            mealType: (recipe as any).meal_type, // For weekly menu
            show_nutrition_only: recipe.show_nutrition_only || false, // Pass through the flag
          };
        })
      );
      
      // Detect if this is a weekly menu response (has day_name and meal_type metadata)
      const isWeeklyMenu = recipeResults.length > 0 && recipeResults.every(r => r.dayName && r.mealType);
      
      const assistantMessage: Message = {
        id: (Date.now() + 1).toString(),
        role: 'assistant',
        content: response.reply,
        timestamp: new Date(),
        recipes: recipeResults,
        isWeeklyMenu: isWeeklyMenu,
      };

      setMessages((prev) => [...prev, assistantMessage]);
    } catch (error) {
      console.error('Chat error:', error);
      const errorMessage: Message = {
        id: (Date.now() + 1).toString(),
        role: 'assistant',
        content: 'Sorry, I encountered an error. Please try again.',
        timestamp: new Date(),
      };
      setMessages((prev) => [...prev, errorMessage]);
    } finally {
      setIsLoading(false);
    }
  };

  const handleRecipeClick = async (recipe: ChatRecipe) => {
    try {
      // For modified recipes (ID starts with "modified_" or "session_"), check if we have fullRecipe data first
      const isModified = recipe.id.startsWith('modified_') || recipe.id.startsWith('session_');
      if (isModified && recipe.fullRecipe && recipe.fullRecipe.ingredients?.length > 0) {
        console.log('Using stored modified recipe data:', recipe.fullRecipe);
        const modalRecipe = {
          id: recipe.id,
          name: recipe.fullRecipe.name || recipe.name,
          category: recipe.category,
          source: recipe.source,
          servings: recipe.fullRecipe.servings || 4,
          totalTime: recipe.fullRecipe.total_time_minutes || recipe.time || 0,
          keywords: recipe.keywords || recipe.fullRecipe.tags || [],
          calories: recipe.calories || 0,
          protein: recipe.protein || 0,
          carbs: recipe.carbs || 0,
          fat: recipe.fat || 0,
          ingredients: Array.isArray(recipe.fullRecipe.ingredients) 
            ? recipe.fullRecipe.ingredients.map((ing: any) => ({
                name: ing.name || '',
                quantity: ing.quantity?.toString() || '',
                unit: ing.unit || ''
              }))
            : [],
          steps: Array.isArray(recipe.fullRecipe.steps)
            ? recipe.fullRecipe.steps.map((step: any) => ({
                number: step.step_number || 0,
                instruction: step.instruction || step
              }))
            : []
        };
        setSelectedRecipe(modalRecipe);
        setShowRecipeModal(true);
      }
      // Check if we have a real recipe ID (from dataset/ChromaDB)
      else if (recipe.id && !recipe.id.startsWith('chat-recipe-')) {
        console.log('Fetching full recipe details for ID:', recipe.id);
        // Fetch complete recipe data from backend (pass sessionId for modified recipes)
        const fullRecipe = await getRecipeById(recipe.id, sessionId);
        setSelectedRecipe(fullRecipe);
        setShowRecipeModal(true);
      } else if (recipe.fullRecipe && recipe.fullRecipe.ingredients?.length > 0) {
        // Only use fullRecipe if it actually has ingredients
        console.log('Using stored recipe data:', recipe.fullRecipe);
        
        const modalRecipe = {
          id: recipe.id,
          name: recipe.fullRecipe.name || recipe.name,
          category: recipe.category,
          source: recipe.source,
          servings: recipe.fullRecipe.servings || 4,
          totalTime: recipe.fullRecipe.total_time_minutes || recipe.time || 0,
          ingredients: Array.isArray(recipe.fullRecipe.ingredients) 
            ? recipe.fullRecipe.ingredients.map((ing: any) => ({
                name: ing.name || '',
                quantity: ing.quantity?.toString() || '',
                unit: ing.unit || ''
              }))
            : [],
          steps: Array.isArray(recipe.fullRecipe.steps)
            ? recipe.fullRecipe.steps.map((step: any, index: number) => ({
                number: step.step_number || index + 1,
                instruction: step.instruction || (typeof step === 'string' ? step : '')
              }))
            : [],
          calories: recipe.calories || 0,
          protein: recipe.protein || 0,
          carbs: recipe.carbs || 0,
          fat: recipe.fat || 0,
          keywords: recipe.keywords || [],
        };
        
        setSelectedRecipe(modalRecipe);
        setShowRecipeModal(true);
      }
    } catch (error) {
      console.error('Failed to fetch recipe:', error);
    }
  };

  return (
    <div className="h-screen flex flex-col bg-gray-50">
      {/* Header */}
      <div className="bg-white border-b border-gray-200 px-4 py-4">
        <div className="max-w-4xl mx-auto flex items-center justify-between">
          <div>
            <h1 className="text-2xl font-bold text-gray-900">AI Assistant</h1>
            <p className="text-sm text-gray-600">Ask me anything about recipes and meal planning</p>
          </div>
          <button className="px-4 py-2 text-sm text-gray-600 hover:text-gray-900 hover:bg-gray-100 rounded-lg transition-colors">
            New Chat
          </button>
        </div>
      </div>

      {/* Messages Area */}
      <div className="flex-1 overflow-y-auto px-4 py-6">
        <div className="max-w-4xl mx-auto">
          {messages.length === 0 ? (
            <div className="flex flex-col items-center justify-center h-full py-12">
              <div className="text-5xl mb-6">🍳</div>
              <h2 className="text-2xl font-bold text-gray-900 mb-2">How can I help you today?</h2>
              <p className="text-gray-600 mb-8">Choose a suggestion or type your own message</p>

              {/* Starter Prompts */}
              <div className="grid grid-cols-1 sm:grid-cols-2 gap-3 w-full max-w-2xl">
                {starterPrompts.map((prompt) => (
                  <button
                    key={prompt}
                    onClick={() => setInput(prompt)}
                    className="px-4 py-3 bg-white border border-gray-200 rounded-lg text-left hover:border-emerald-500 hover:bg-emerald-50 transition-colors"
                  >
                    <span className="text-gray-900">{prompt}</span>
                  </button>
                ))}
              </div>
            </div>
          ) : (
            <div className="space-y-6">
              {messages.map((message) => (
                <div
                  key={message.id}
                  className={`flex flex-col ${message.role === 'user' ? 'items-end' : 'items-start'}`}
                >
                  <div
                    className={`max-w-[80%] rounded-lg px-4 py-3 ${
                      message.role === 'user'
                        ? 'bg-emerald-600 text-white'
                        : 'bg-white border border-gray-200 text-gray-900'
                    }`}
                  >
                    <p className="whitespace-pre-wrap">{message.content}</p>
                    <p
                      className={`text-xs mt-2 ${
                        message.role === 'user' ? 'text-emerald-100' : 'text-gray-500'
                      }`}
                    >
                      {message.timestamp.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })}
                    </p>
                  </div>

                  {/* Recipe Cards or Weekly Menu */}
                  {message.role === 'assistant' && message.recipes && message.recipes.length > 0 && (
                    <>
                      {message.isWeeklyMenu ? (
                        // Weekly Menu Display - organized by day
                        <div className="mt-4 w-full">
                          {['Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday', 'Saturday', 'Sunday'].map((dayName) => {
                            const dayRecipes = message.recipes?.filter(r => r.dayName === dayName) || [];
                            if (dayRecipes.length === 0) return null;

                            const breakfast = dayRecipes.find(r => r.mealType === 'breakfast');
                            const lunch = dayRecipes.find(r => r.mealType === 'lunch');
                            const dinner = dayRecipes.find(r => r.mealType === 'dinner');

                            return (
                              <div key={dayName} className="mb-4">
                                <h3 className="text-sm font-semibold text-gray-700 mb-2">{dayName}</h3>
                                <div className="grid grid-cols-1 sm:grid-cols-3 gap-3">
                                  {[breakfast, lunch, dinner].map((recipe, idx) => {
                                    if (!recipe) return (
                                      <div key={idx} className="h-32 border-2 border-dashed border-gray-200 rounded-xl"></div>
                                    );
                                    return (
                                      <div
                                        key={recipe.id}
                                        onClick={() => handleRecipeClick(recipe)}
                                        className="relative h-32 bg-linear-to-br from-white to-gray-50 border-2 border-gray-200 rounded-xl p-3 hover:border-emerald-500 hover:shadow-md transition-all cursor-pointer flex flex-col"
                                      >
                                        <div>
                                          <div className="text-xs text-emerald-600 font-medium mb-1 capitalize">
                                            {recipe.mealType}
                                          </div>
                                          <div className="text-sm font-semibold text-gray-900 mb-2 line-clamp-2 leading-tight">
                                            {recipe.name}
                                          </div>
                                          <div className="flex items-center gap-2 text-xs text-gray-600 mb-2">
                                            <span className="flex items-center gap-1 whitespace-nowrap">
                                              <span className="w-1.5 h-1.5 bg-emerald-500 rounded-full"></span>
                                              {recipe.calories || 0} cal
                                            </span>
                                            <span className="text-gray-400">•</span>
                                            <span className="flex items-center gap-1 whitespace-nowrap">
                                              <span className="w-1.5 h-1.5 bg-orange-500 rounded-full"></span>
                                              {formatTime(recipe.time || 0)}
                                            </span>
                                          </div>
                                        </div>
                                        <div className="flex gap-1 mt-auto flex-wrap">
                                          <span className="px-1.5 py-0.5 bg-blue-50 text-blue-700 rounded text-[10px] font-medium whitespace-nowrap">
                                            P {Math.round(recipe.protein || 0)}g
                                          </span>
                                          <span className="px-1.5 py-0.5 bg-orange-50 text-orange-700 rounded text-[10px] font-medium whitespace-nowrap">
                                            C {Math.round(recipe.carbs || 0)}g
                                          </span>
                                          <span className="px-1.5 py-0.5 bg-purple-50 text-purple-700 rounded text-[10px] font-medium whitespace-nowrap">
                                            F {Math.round(recipe.fat || 0)}g
                                          </span>
                                        </div>
                                      </div>
                                    );
                                  })}
                                </div>
                              </div>
                            );
                          })}
                        </div>
                      ) : message.recipes.length === 1 && message.recipes[0].show_nutrition_only ? (
                        // Nutrition Only Display (like RecipeDisplay component)
                        <div className="mt-3 w-full max-w-2xl">
                          <h3 className="text-lg font-semibold mb-3">Nutrition (per serving)</h3>
                          <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
                            <div className="bg-gray-50 rounded-lg p-4 text-center">
                              <p className="text-2xl font-bold text-orange-600">
                                {Math.round(message.recipes[0].calories || 0)}
                              </p>
                              <p className="text-sm text-gray-600">Calories</p>
                            </div>
                            <div className="bg-gray-50 rounded-lg p-4 text-center">
                              <p className="text-2xl font-bold text-blue-600">
                                {Math.round(message.recipes[0].protein || 0)}g
                              </p>
                              <p className="text-sm text-gray-600">Protein</p>
                            </div>
                            <div className="bg-gray-50 rounded-lg p-4 text-center">
                              <p className="text-2xl font-bold text-green-600">
                                {Math.round(message.recipes[0].carbs || 0)}g
                              </p>
                              <p className="text-sm text-gray-600">Carbs</p>
                            </div>
                            <div className="bg-gray-50 rounded-lg p-4 text-center">
                              <p className="text-2xl font-bold text-yellow-600">
                                {Math.round(message.recipes[0].fat || 0)}g
                              </p>
                              <p className="text-sm text-gray-600">Fat</p>
                            </div>
                          </div>
                        </div>
                      ) : (
                        // Regular Recipe Cards
                        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-3 mt-3 w-full max-w-3xl">
                          {message.recipes.map((recipe) => (
                            <div
                              key={recipe.id}
                              onClick={() => handleRecipeClick(recipe)}
                              className="relative h-32 bg-linear-to-br from-white to-gray-50 border-2 border-gray-200 rounded-xl p-3 hover:border-emerald-500 hover:shadow-md transition-all cursor-pointer flex flex-col"
                            >
                              <div>
                                <div className="text-sm font-semibold text-gray-900 mb-2 line-clamp-2 leading-tight min-h-10">
                                  {recipe.name}
                                </div>
                                <div className="flex items-center gap-2 text-xs text-gray-600 mb-2">
                                  <span className="flex items-center gap-1 whitespace-nowrap">
                                    <span className="w-1.5 h-1.5 bg-emerald-500 rounded-full"></span>
                                    {recipe.calories || 0} cal
                                  </span>
                                  <span className="text-gray-400">•</span>
                                  <span className="flex items-center gap-1 whitespace-nowrap">
                                    <span className="w-1.5 h-1.5 bg-orange-500 rounded-full"></span>
                                    {formatTime(recipe.time || 0)}
                                  </span>
                                </div>
                              </div>
                              <div className="flex gap-1 mt-auto flex-wrap">
                                <span className="px-1.5 py-0.5 bg-blue-50 text-blue-700 rounded text-[10px] font-medium whitespace-nowrap">
                                  P {Math.round(recipe.protein || 0)}g
                                </span>
                                <span className="px-1.5 py-0.5 bg-orange-50 text-orange-700 rounded text-[10px] font-medium whitespace-nowrap">
                                  C {Math.round(recipe.carbs || 0)}g
                                </span>
                                <span className="px-1.5 py-0.5 bg-purple-50 text-purple-700 rounded text-[10px] font-medium whitespace-nowrap">
                                  F {Math.round(recipe.fat || 0)}g
                                </span>
                              </div>
                            </div>
                          ))}
                        </div>
                      )}
                    </>
                  )}
                </div>
              ))}

              {isLoading && (
                <div className="flex justify-start">
                  <div className="bg-white border border-gray-200 rounded-lg px-4 py-3">
                    <Loader2 className="animate-spin text-gray-400" size={20} />
                  </div>
                </div>
              )}
            </div>
          )}
        </div>
      </div>

      {/* Input Area */}
      <div className="bg-white border-t border-gray-200 px-4 py-4">
        <div className="max-w-4xl mx-auto">
          {/* Image Preview */}
          {imagePreview && (
            <div className="mb-3 relative inline-block">
              <img src={imagePreview} alt="Preview" className="max-h-32 rounded-lg border-2 border-emerald-500" />
              <button
                onClick={() => {
                  setSelectedImage(null);
                  setImagePreview(null);
                }}
                className="absolute -top-2 -right-2 bg-red-500 text-white rounded-full p-1 hover:bg-red-600"
              >
                <X size={16} />
              </button>
            </div>
          )}
          
          <div className="flex gap-2 items-end">
            <div className="flex gap-2">
              <input
                type="file"
                accept="image/*"
                onChange={handleImageSelect}
                className="hidden"
                id="image-upload"
              />
              <label
                htmlFor="image-upload"
                className="p-2 text-gray-600 hover:text-emerald-600 hover:bg-emerald-50 rounded-lg transition-colors cursor-pointer"
                title="Upload image"
              >
                <ImageIcon size={20} />
              </label>
            </div>

            <div className="flex-1 relative">
              <textarea
                value={input}
                onChange={(e) => setInput(e.target.value)}
                onKeyDown={(e) => {
                  if (e.key === 'Enter' && !e.shiftKey) {
                    e.preventDefault();
                    handleSend();
                  }
                }}
                placeholder="Type a message, paste a URL, or upload an image..."
                rows={1}
                className="w-full px-4 py-3 border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-emerald-500 focus:border-transparent resize-none"
                style={{ minHeight: '44px', maxHeight: '120px' }}
              />
            </div>

            <button
              onClick={handleSend}
              disabled={(!input.trim() && !selectedImage) || isLoading}
              className="p-3 bg-emerald-600 text-white rounded-lg hover:bg-emerald-700 disabled:bg-gray-300 disabled:cursor-not-allowed transition-colors"
            >
              {isLoading ? <Loader2 size={20} className="animate-spin" /> : <Send size={20} />}
            </button>
          </div>
        </div>
      </div>

      {/* Recipe Detail Modal */}
      {showRecipeModal && selectedRecipe && (
        <RecipeDetailModal
          isOpen={showRecipeModal}
          recipe={selectedRecipe}
          onClose={() => {
            setShowRecipeModal(false);
            setSelectedRecipe(null);
          }}
        />
      )}
    </div>
  );
}
