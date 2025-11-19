'use client';

import { useState } from 'react';
import { sendChatMessage, Recipe, WeeklyMenu } from '@/lib/apiClient';

export default function ChatPlanning() {
  const [message, setMessage] = useState('');
  const [sessionId] = useState(() => `session_${Date.now()}`);
  const [messages, setMessages] = useState<Array<{ role: 'user' | 'assistant'; content: string }>>([]);
  const [loading, setLoading] = useState(false);
  const [suggestedRecipes, setSuggestedRecipes] = useState<Recipe[]>([]);
  const [weeklyMenu, setWeeklyMenu] = useState<WeeklyMenu | null>(null);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!message.trim()) return;

    const userMessage = message;
    setMessage('');
    setMessages(prev => [...prev, { role: 'user', content: userMessage }]);
    setLoading(true);

    try {
      const response = await sendChatMessage(sessionId, userMessage);
      
      setMessages(prev => [...prev, { role: 'assistant', content: response.reply }]);
      setSuggestedRecipes(response.suggested_recipes);
      setWeeklyMenu(response.weekly_menu || null);
    } catch (err) {
      setMessages(prev => [...prev, { 
        role: 'assistant', 
        content: 'Sorry, something went wrong. Please try again.' 
      }]);
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="space-y-6">
      {/* AI-Powered Chat */}
      <div className="bg-white rounded-lg shadow-md p-6">
        <h2 className="text-2xl font-semibold mb-4">🤖 AI Recipe Assistant</h2>
        
        <div className="bg-gradient-to-r from-orange-50 to-yellow-50 border border-orange-200 rounded-lg p-4 mb-4">
          <p className="text-sm text-gray-700 mb-2">
            <strong>I can help you with:</strong>
          </p>
          <ul className="text-sm text-gray-600 space-y-1 ml-4">
            <li>🥬 Finding recipes based on ingredients you have</li>
            <li>📅 Planning your weekly meal schedule</li>
            <li>🔍 Discovering new recipes by category, cuisine, or dietary needs</li>
            <li>� Getting personalized recommendations</li>
          </ul>
          <p className="text-xs text-gray-500 mt-3 italic">
            Just tell me what you need in natural language!
          </p>
        </div>

        {/* Chat Messages */}
        <div className="bg-gray-50 rounded-lg p-4 mb-4 h-64 overflow-y-auto">
          {messages.length === 0 ? (
            <p className="text-gray-400 text-center py-8">
              Start a conversation...
            </p>
          ) : (
            <div className="space-y-3">
              {messages.map((msg, idx) => (
                <div
                  key={idx}
                  className={`p-3 rounded-lg ${
                    msg.role === 'user'
                      ? 'bg-orange-100 ml-8'
                      : 'bg-white mr-8'
                  }`}
                >
                  <p className="text-sm font-medium mb-1">
                    {msg.role === 'user' ? 'You' : 'Assistant'}
                  </p>
                  <p className="text-gray-700">{msg.content}</p>
                </div>
              ))}
            </div>
          )}
        </div>

        {/* Input Form */}
        <form onSubmit={handleSubmit} className="flex gap-2">
          <input
            type="text"
            value={message}
            onChange={(e) => setMessage(e.target.value)}
            placeholder="Type your message..."
            className="flex-1 px-4 py-2 border border-gray-300 rounded-md focus:ring-2 focus:ring-orange-500 focus:border-transparent"
          />
          <button
            type="submit"
            disabled={loading || !message.trim()}
            className="bg-orange-500 text-white py-2 px-6 rounded-md font-medium hover:bg-orange-600 disabled:bg-gray-300 disabled:cursor-not-allowed transition-colors"
          >
            {loading ? '...' : 'Send'}
          </button>
        </form>
      </div>

      {/* Suggested Recipes */}
      {suggestedRecipes.length > 0 && (
        <div className="bg-white rounded-lg shadow-md p-6">
          <h3 className="text-xl font-semibold mb-4">Suggested Recipes</h3>
          <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
            {suggestedRecipes.map((recipe, idx) => (
              <div key={idx} className="border rounded-lg p-4 hover:shadow-md transition-shadow">
                <h4 className="font-semibold mb-2">{recipe.name}</h4>
                <p className="text-sm text-gray-600 mb-2">{recipe.description}</p>
                <div className="text-xs text-gray-500">
                  <span>⏱️ {recipe.total_time_minutes} min</span>
                  <span className="ml-3">🍽️ {recipe.servings} servings</span>
                </div>
              </div>
            ))}
          </div>
        </div>
      )}

      {/* Weekly Menu */}
      {weeklyMenu && (
        <div className="bg-white rounded-lg shadow-md p-6">
          <h3 className="text-xl font-semibold mb-4">{weeklyMenu.name}</h3>
          <p className="text-sm text-gray-600 mb-4">
            Week starting: {weeklyMenu.week_start_date}
          </p>
          <div className="space-y-3">
            {weeklyMenu.days.map((day, idx) => (
              <div key={idx} className="border-l-4 border-orange-500 pl-4 py-2">
                <h4 className="font-semibold">{day.day_name}</h4>
                <div className="text-sm text-gray-600 space-y-1">
                  {day.breakfast && <p>🌅 {day.breakfast.name}</p>}
                  {day.lunch && <p>☀️ {day.lunch.name}</p>}
                  {day.dinner && <p>🌙 {day.dinner.name}</p>}
                </div>
              </div>
            ))}
          </div>
        </div>
      )}
    </div>
  );
}
