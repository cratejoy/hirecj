import { useState } from 'react';

const ExperienceSection = () => {
  const [activeMetrics, setActiveMetrics] = useState<number | null>(null);

  const toggleMetrics = (index: number) => {
    if (activeMetrics === index) {
      setActiveMetrics(null);
    } else {
      setActiveMetrics(index);
    }
  };

  return (
    <section id="experience" className="profile-section section-card p-6">
      <h2 className="text-xl font-bold mb-4">Experience</h2>
      
      {/* Job 1 */}
      <div className="mb-8 border-b border-linkedin-border pb-6">
        <div className="flex items-start">
          <div className="mr-4">
            <div className="w-12 h-12 bg-cratejoy-teal rounded flex items-center justify-center text-white">
              <span className="text-xl font-bold">CJ</span>
            </div>
          </div>
          <div className="flex-1">
            <h3 className="text-lg font-medium">Autonomous CX & Growth Officer</h3>
            <p className="text-gray-600">Cratejoy • 2025—Present</p>
            
            <div className="mt-3 space-y-2">
              <p className="flex items-center cursor-pointer" onClick={() => toggleMetrics(0)}>
                • Resolved 7.3 hrs of daily support labor per store
                <svg 
                  xmlns="http://www.w3.org/2000/svg" 
                  className={`h-4 w-4 ml-2 transition-transform duration-300 ${activeMetrics === 0 ? 'rotate-180' : ''}`} 
                  fill="none" 
                  viewBox="0 0 24 24" 
                  stroke="currentColor"
                >
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M19 9l-7 7-7-7" />
                </svg>
              </p>
              {activeMetrics === 0 && (
                <div className="bg-linkedin-gray rounded-md p-3 text-sm mt-1">
                  <p className="text-cratejoy-teal font-medium">Raw Metrics:</p>
                  <p>From 9.5 hours average support time to 2.2 hours - 76.8% reduction</p>
                  <p>Average response time: 1m 48s vs previous 42m</p>
                </div>
              )}
              
              <p className="flex items-center cursor-pointer" onClick={() => toggleMetrics(1)}>
                • Lifted PDP conversion +9.4% via copy mined from 10,000 reviews
                <svg 
                  xmlns="http://www.w3.org/2000/svg" 
                  className={`h-4 w-4 ml-2 transition-transform duration-300 ${activeMetrics === 1 ? 'rotate-180' : ''}`} 
                  fill="none" 
                  viewBox="0 0 24 24" 
                  stroke="currentColor"
                >
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M19 9l-7 7-7-7" />
                </svg>
              </p>
              {activeMetrics === 1 && (
                <div className="bg-linkedin-gray rounded-md p-3 text-sm mt-1">
                  <p className="text-cratejoy-teal font-medium">Raw Metrics:</p>
                  <p>A/B tested 215 product descriptions across 47 stores</p>
                  <p>Generated $143,920 incremental monthly revenue</p>
                </div>
              )}
              
              <p className="flex items-center cursor-pointer" onClick={() => toggleMetrics(2)}>
                • Generated $7,861 in weekly upsell GMV with surprise-and-delight rules
                <svg 
                  xmlns="http://www.w3.org/2000/svg" 
                  className={`h-4 w-4 ml-2 transition-transform duration-300 ${activeMetrics === 2 ? 'rotate-180' : ''}`} 
                  fill="none" 
                  viewBox="0 0 24 24" 
                  stroke="currentColor"
                >
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M19 9l-7 7-7-7" />
                </svg>
              </p>
              {activeMetrics === 2 && (
                <div className="bg-linkedin-gray rounded-md p-3 text-sm mt-1">
                  <p className="text-cratejoy-teal font-medium">Raw Metrics:</p>
                  <p>12.3% acceptance rate on personalized upsell offers</p>
                  <p>Return customers increased by 18.7%</p>
                </div>
              )}
              
              <p className="flex items-center cursor-pointer" onClick={() => toggleMetrics(3)}>
                • Brought average first-reply time down from 42 min → 1 min 30 sec
                <svg 
                  xmlns="http://www.w3.org/2000/svg" 
                  className={`h-4 w-4 ml-2 transition-transform duration-300 ${activeMetrics === 3 ? 'rotate-180' : ''}`} 
                  fill="none" 
                  viewBox="0 0 24 24" 
                  stroke="currentColor"
                >
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M19 9l-7 7-7-7" />
                </svg>
              </p>
              {activeMetrics === 3 && (
                <div className="bg-linkedin-gray rounded-md p-3 text-sm mt-1">
                  <p className="text-cratejoy-teal font-medium">Raw Metrics:</p>
                  <p>96.5% of initial responses under 5 minutes</p>
                  <p>CSAT improved from 4.2 to 4.8/5 stars</p>
                </div>
              )}
            </div>
            
            <p className="text-sm text-linkedin-blue mt-2">(✨ click for raw metrics)</p>
          </div>
        </div>
      </div>
      
      {/* Job 2 */}
      <div className="mb-8 border-b border-linkedin-border pb-6">
        <div className="flex items-start">
          <div className="mr-4">
            <div className="w-12 h-12 bg-cratejoy-teal rounded flex items-center justify-center text-white">
              <span className="text-xl font-bold">CJ</span>
            </div>
          </div>
          <div>
            <h3 className="text-lg font-medium">Reputation Agent</h3>
            <p className="text-gray-600">Cratejoy • 2025 (beta)</p>
            
            <div className="mt-3 space-y-2">
              <p>• Auto-replied to 100% of reviews; reduced negative-review turnaround from 18 h → 5 h 48 min</p>
              <p>• Raised marketplace NPS 5 points in six weeks</p>
            </div>
          </div>
        </div>
      </div>
      
      {/* Job 3 */}
      <div>
        <div className="flex items-start">
          <div className="mr-4">
            <div className="w-12 h-12 bg-cratejoy-teal rounded flex items-center justify-center text-white">
              <span className="text-xl font-bold">CJ</span>
            </div>
          </div>
          <div>
            <h3 className="text-lg font-medium">Support Autopilot</h3>
            <p className="text-gray-600">Cratejoy • 2024 (alpha)</p>
            
            <div className="mt-3 space-y-2">
              <p>• Deleted 70% of "Where-is-my-order?" tickets day-one</p>
              <p>• Uncovered packaging defect saving $12k in refund leakage</p>
            </div>
          </div>
        </div>
      </div>
    </section>
  );
};

export default ExperienceSection;
