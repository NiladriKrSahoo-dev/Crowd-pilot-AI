import React from 'react';
import { AlertTriangle, Video, Map, BarChart3 } from 'lucide-react';

function App() {
  return (
    <div className="flex h-screen bg-gray-950 text-white">
      {/* Sidebar */}
      <nav className="w-64 border-r border-gray-800 p-6 flex flex-col">
        <h1 className="text-xl font-bold text-red-500 mb-10">CrowdPilot AI</h1>
        <div className="space-y-6 flex-1">
          <div className="flex items-center gap-3 text-red-500 cursor-pointer hover:text-red-400"><Video size={20}/> Live Feed</div>
          <div className="flex items-center gap-3 text-gray-400 cursor-pointer hover:text-gray-200"><Map size={20}/> Venue Map</div>
          <div className="flex items-center gap-3 text-gray-400 cursor-pointer hover:text-gray-200"><BarChart3 size={20}/> Analytics</div>
        </div>
      </nav>

      {/* Main Content Area */}
      <main className="flex-1 p-8 flex flex-col">
        <header className="flex justify-between items-center mb-8">
          <h2 className="text-2xl font-semibold">Live Monitoring: Main Entrance</h2>
          <div className="bg-red-900/30 border border-red-500 text-red-500 px-4 py-2 rounded flex items-center gap-2">
            <AlertTriangle size={20}/> RISK LEVEL: HIGH
          </div>
        </header>
        
        {/* Placeholder for Video Feed */}
        <div className="w-full flex-1 bg-gray-900 rounded-lg border-2 border-dashed border-gray-700 flex items-center justify-center text-gray-500">
          AI Video Feed Loading...
        </div>
      </main>
    </div>
  );
}

export default App;