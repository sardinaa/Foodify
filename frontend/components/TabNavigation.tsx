'use client';

import Link from 'next/link';
import { usePathname } from 'next/navigation';
import { Home, Search, MessageCircle } from 'lucide-react';

export default function TabNavigation() {
  const pathname = usePathname();

  const tabs = [
    { name: 'Home', path: '/home', icon: Home },
    { name: 'Recipes', path: '/recipes', icon: Search },
    { name: 'Chat', path: '/chat', icon: MessageCircle },
  ];

  return (
    <>
      {/* Desktop Sidebar */}
      <nav className="hidden md:flex fixed left-0 top-0 h-full w-20 flex-col items-center bg-white border-r border-gray-200 py-8 z-50">
        <div className="mb-12">
          <div className="text-3xl">🍳</div>
        </div>
        
        <div className="flex flex-col gap-6">
          {tabs.map((tab) => {
            const Icon = tab.icon;
            const isActive = pathname === tab.path;
            
            return (
              <Link
                key={tab.path}
                href={tab.path}
                className={`flex flex-col items-center gap-1 px-4 py-3 rounded-lg transition-colors ${
                  isActive
                    ? 'text-emerald-600 bg-emerald-50'
                    : 'text-gray-600 hover:text-emerald-600 hover:bg-gray-50'
                }`}
                title={tab.name}
              >
                <Icon size={24} />
                <span className="text-xs font-medium">{tab.name}</span>
              </Link>
            );
          })}
        </div>
      </nav>

      {/* Mobile Bottom Navigation */}
      <nav className="md:hidden fixed bottom-0 left-0 right-0 bg-white border-t border-gray-200 z-50">
        <div className="flex justify-around items-center h-16">
          {tabs.map((tab) => {
            const Icon = tab.icon;
            const isActive = pathname === tab.path;
            
            return (
              <Link
                key={tab.path}
                href={tab.path}
                className={`flex flex-col items-center gap-1 px-4 py-2 transition-colors ${
                  isActive
                    ? 'text-emerald-600'
                    : 'text-gray-600'
                }`}
              >
                <Icon size={24} />
                <span className="text-xs font-medium">{tab.name}</span>
              </Link>
            );
          })}
        </div>
      </nav>
    </>
  );
}
