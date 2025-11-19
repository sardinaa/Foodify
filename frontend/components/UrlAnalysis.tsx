'use client';

import { useState } from 'react';
import { analyzeUrl, Recipe, NutritionSummary } from '@/lib/apiClient';
import RecipeDisplay from './RecipeDisplay';

export default function UrlAnalysis() {
  const [url, setUrl] = useState('');
  const [loading, setLoading] = useState(false);
  const [result, setResult] = useState<{
    recipe: Recipe;
    nutrition: NutritionSummary;
    tags: string[];
  } | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [showSocialWarning, setShowSocialWarning] = useState(false);

  const isSocialMediaUrl = (url: string): boolean => {
    const socialDomains = [
      'instagram.com', 'tiktok.com', 'twitter.com', 'x.com',
      'facebook.com', 'fb.com', 'snapchat.com'
    ];
    try {
      const domain = new URL(url).hostname.replace('www.', '').toLowerCase();
      return socialDomains.some(social => domain.includes(social));
    } catch {
      return false;
    }
  };

  const handleUrlChange = (value: string) => {
    setUrl(value);
    setShowSocialWarning(isSocialMediaUrl(value));
  };

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!url) {
      setError('Please enter a URL');
      return;
    }

    setLoading(true);
    setError(null);

    try {
      const response = await analyzeUrl(url);
      setResult(response);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Analysis failed');
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="space-y-6">
      {/* URL Form */}
      <div className="bg-white rounded-lg shadow-md p-6">
        <h2 className="text-2xl font-semibold mb-4">Extract Recipe from URL</h2>
        <form onSubmit={handleSubmit} className="space-y-4">
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-2">
              Recipe URL
            </label>
            <input
              type="url"
              value={url}
              onChange={(e) => handleUrlChange(e.target.value)}
              placeholder="https://example.com/recipe"
              className="w-full px-4 py-2 border border-gray-300 rounded-md focus:ring-2 focus:ring-orange-500 focus:border-transparent"
            />
          </div>

          {showSocialWarning && (
            <div className="bg-blue-50 border border-blue-200 text-blue-800 p-3 rounded-md text-sm">
              <strong>💡 Social Media Tip:</strong> We'll try to extract content from this URL, but social platforms sometimes block automated access.
              If it doesn't work, simply <strong>copy the caption</strong> and use the <strong>Chat</strong> tab for guaranteed results!
            </div>
          )}

          {error && (
            <div className="bg-red-50 text-red-700 p-3 rounded-md">
              {error}
            </div>
          )}

          <button
            type="submit"
            disabled={loading || !url}
            className="w-full bg-orange-500 text-white py-3 px-4 rounded-md font-medium hover:bg-orange-600 disabled:bg-gray-300 disabled:cursor-not-allowed transition-colors"
          >
            {loading ? 'Extracting...' : 'Extract Recipe'}
          </button>
        </form>
      </div>

      {/* Results */}
      {result && (
        <RecipeDisplay
          recipe={result.recipe}
          nutrition={result.nutrition}
          tags={result.tags}
        />
      )}
    </div>
  );
}
