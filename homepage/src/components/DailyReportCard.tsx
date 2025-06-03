import React from 'react';

interface DailyReportCardProps {
  className?: string;
}

const DailyReportCard: React.FC<DailyReportCardProps> = ({ className = '' }) => {
  return (
    <div className={`w-full max-w-3xl mx-auto bg-chat-bg text-white rounded-lg overflow-hidden ${className}`}>
      {/* Header */}
      <div className="p-4 border-b border-gray-700">
        <div className="flex items-center">
          <div className="bg-blue-400 rounded w-6 h-6 flex items-center justify-center mr-2">
            <span className="text-xs font-bold">📊</span>
          </div>
          <div>
            <h2 className="text-lg font-bold">Support Agent v1 Dashboard</h2>
            <div className="text-xs text-gray-400">Daily CX Pulse • May 20, 2025 • 07:00 AM</div>
          </div>
        </div>
      </div>

      {/* Yesterday at a Glance */}
      <div className="p-4 border-b border-gray-700">
        <div className="flex items-center mb-3">
          <div className="w-2 h-2 bg-blue-400 rounded-full mr-2"></div>
          <h3 className="font-semibold">Yesterday at a Glance</h3>
        </div>
        
        <div className="space-y-3 text-sm">
          <div className="flex justify-between">
            <span className="text-gray-300">Tickets received</span>
            <span className="font-mono">152</span>
          </div>
          
          <div className="flex justify-between">
            <span className="text-gray-300">Auto-resolved by Agent</span>
            <span className="font-mono text-green-400">109 (71%)</span>
          </div>
          
          <div className="flex justify-between">
            <span className="text-gray-300">Human-handled</span>
            <span className="font-mono">43</span>
          </div>
          
          <div className="flex justify-between">
            <span className="text-gray-300">Avg first-reply time</span>
            <span className="font-mono">
              <span className="text-green-400">2m Agent</span> | <span className="text-yellow-400">38m Human</span>
            </span>
          </div>
          
          <div className="flex justify-between">
            <span className="text-gray-300">CX hours saved</span>
            <span className="font-mono text-green-400">7.3h (≈ $183 labor)</span>
          </div>
        </div>
      </div>

      {/* CSAT Snapshot */}
      <div className="p-4 border-b border-gray-700">
        <div className="flex items-center mb-3">
          <span className="text-yellow-400 mr-2">★</span>
          <h3 className="font-semibold">CSAT Snapshot</h3>
        </div>
        
        <div className="space-y-3 text-sm">
          <div className="flex justify-between">
            <span className="text-gray-300">Agent-handled</span>
            <span className="font-mono text-green-400">4.78★ (+0.06)</span>
          </div>
          
          <div className="flex justify-between">
            <span className="text-gray-300">Human-handled</span>
            <span className="font-mono text-red-400">4.64★ (-0.02)</span>
          </div>
        </div>
      </div>

      {/* Hot-Spot Intents */}
      <div className="p-4 border-b border-gray-700">
        <div className="flex items-center mb-3">
          <span className="text-orange-400 mr-2">🔥</span>
          <h3 className="font-semibold">Hot-Spot Intents</h3>
          <span className="text-xs text-gray-400 ml-2">(vol Δ vs 7-day avg)</span>
        </div>
        
        <div className="space-y-3 text-sm">
          <div className="flex justify-between">
            <span className="text-gray-300">WISMO</span>
            <span className="font-mono text-yellow-400">+12%</span>
          </div>
          
          <div className="flex justify-between">
            <span className="text-gray-300">Address change</span>
            <span className="font-mono text-green-400">-5%</span>
          </div>
          
          <div className="flex justify-between">
            <span className="text-gray-300">"Cancel next box"</span>
            <span className="font-mono text-yellow-400">+3%</span>
          </div>
          
          <div className="flex items-center mt-2">
            <span className="text-yellow-400 text-xs mr-2">⚠</span>
            <span className="text-xs text-gray-400">spike flag if any intent exceeds threshold</span>
          </div>
        </div>
      </div>

      {/* Bad-Experience Alerts */}
      <div className="p-4 border-b border-gray-700">
        <div className="flex items-center mb-3">
          <span className="text-yellow-400 mr-2">⚠</span>
          <h3 className="font-semibold">Bad-Experience Alerts</h3>
        </div>
        
        <div className="space-y-3 text-sm">
          <div className="flex justify-between">
            <span className="text-gray-300">Open tickets (over 24h)</span>
            <span className="font-mono text-yellow-400">2 → links</span>
          </div>
          
          <div className="flex justify-between">
            <span className="text-gray-300">Negative CSAT (under 3★)</span>
            <span className="font-mono text-yellow-400">4 → links</span>
          </div>
          
          <div className="flex justify-between">
            <span className="text-gray-300">Carrier delays cluster</span>
            <span className="font-mono text-red-400">FedEx — 12 parcels stuck</span>
          </div>
        </div>
      </div>

      {/* Critical Issue Teasers */}
      <div className="p-4">
        <div className="flex items-center mb-3">
          <span className="text-red-400 mr-2">🚨</span>
          <h3 className="font-semibold">Critical Issue Teasers</h3>
        </div>
        
        <div className="space-y-4 text-sm">
          <div className="border-l-2 border-red-500 pl-3">
            <div className="text-red-400">Angry customer cannot cancel subscription after 3 attempts...</div>
            <div className="flex justify-between text-xs text-gray-400 mt-1">
              <div>2h ago • 👑 VIP customer ($1.2K LTV) • Escalated</div>
              <div>View Ticket #4592</div>
            </div>
          </div>
          
          <div className="border-l-2 border-red-500 pl-3">
            <div className="text-red-400">VIP customer ($2K LTV) received damaged items in last 2 boxes...</div>
            <div className="flex justify-between text-xs text-gray-400 mt-1">
              <div>5h ago • 🔁 Repeat issue • Photos attached</div>
              <div>View Ticket #4587</div>
            </div>
          </div>
          
          <div className="border-l-2 border-yellow-500 pl-3">
            <div className="text-yellow-400">Multiple customers (8) reporting billing issues with May renewal...</div>
            <div className="flex justify-between text-xs text-gray-400 mt-1">
              <div>12h ago • 💰 Payment processor issue suspected</div>
              <div>View Pattern #142</div>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
};

export default DailyReportCard;