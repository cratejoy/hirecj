import React, { useState } from 'react';

const MicroBanner: React.FC = () => {
  const [isVisible, setIsVisible] = useState(true);

  if (!isVisible) return null;

  return (
    <div className="w-full bg-cratejoy-teal py-2 flex relative">
      <div className="w-full max-w-6xl mx-auto px-10 flex items-center justify-center">
        <p className="text-white text-xs font-semibold pr-6">
          ⚡ This résumé belongs to an AI coworker you can hire today — chat to see her work.
        </p>
      </div>
      
      {/* Clear close button with border */}
      <button 
        className="absolute right-4 top-1/2 transform -translate-y-1/2 bg-white border border-gray-300 rounded px-2 py-0.5 text-xs font-medium flex items-center justify-center hover:bg-gray-100"
        onClick={() => setIsVisible(false)}
        aria-label="Dismiss banner"
      >
        Close X
      </button>
    </div>
  );
};

export default MicroBanner;