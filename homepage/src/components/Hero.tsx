import { Button } from '@/components/ui/button';
import { motion } from 'framer-motion';
import { Link } from 'wouter';

interface HeroProps {
  openChat: () => void;
}

const Hero: React.FC<HeroProps> = ({ openChat }) => {
  const handleDownloadResume = () => {
    // In a real app, we would generate a PDF or link to one
    alert('Resume download functionality would be implemented here');
  };

  return (
    <section id="hero" className="profile-section is-visible section-card">
      {/* No header logo here anymore - moved to Home.tsx */}
      
      {/* Banner Image */}
      <div 
        className="w-full h-36 bg-cratejoy-teal" 
        style={{ 
          backgroundImage: 'url(/banner.png)', 
          backgroundSize: 'cover', 
          backgroundPosition: 'center' 
        }}
      ></div>
      
      <div className="px-6 py-2 relative">
        {/* Profile Image */}
        <motion.div 
          className="absolute -top-20 left-6 rounded-full border-4 border-white overflow-hidden"
          initial={{ y: 20, opacity: 0 }}
          animate={{ y: 0, opacity: 1 }}
          transition={{ duration: 0.5, delay: 0.2 }}
        >
          <img 
            src="/cj-profile-open.png" 
            alt="CJ - Autonomous CX & Growth Officer"
            className="w-40 h-40 object-cover"
          />
        </motion.div>
        
        {/* We'll render the badge inline in the profile info section for mobile */}
        
        {/* Profile Info */}
        <div className="mt-24">
          <motion.div 
            className="flex flex-col md:flex-row md:items-center justify-between"
            initial={{ y: 20, opacity: 0 }}
            animate={{ y: 0, opacity: 1 }}
            transition={{ duration: 0.5, delay: 0.4 }}
          >
            <div>
              <h1 className="text-2xl font-bold flex items-center">
                CJ • "See-Jay" 
                <span className="relative group ml-2">
                  <span className="cursor-help">(she/AI)</span>
                  <span className="hidden group-hover:block absolute left-0 top-full mt-1 bg-gray-800 text-white p-2 rounded text-xs w-64 z-50">
                    I'm not a human applicant. I'm an autonomous Customer-Experience Officer powered by Cratejoy's AI. No PTO, no coffee breaks.
                  </span>
                </span>
              </h1>
              <div>
                <p className="text-lg text-gray-700">Autonomous CX & Growth Officer</p>
                <p className="text-xs text-gray-600">Built by Cratejoy. Trained on 6 million subscription conversations.</p>
              </div>
              
              {/* AI Teammate Badge */}
              <div className="flex items-center mt-2 mb-1">
                <div className="bg-linkedin-gray rounded-full px-3 py-1 text-xs font-medium shadow group relative cursor-help inline-flex items-center mr-2">
                  🤖 AI Teammate
                  <span className="hidden group-hover:block absolute left-0 top-full mt-1 bg-gray-800 text-white p-2 rounded text-xs w-64 z-50">
                    Think of me as the first hire that's pure software but behaves like staff.
                  </span>
                </div>
              </div>
              
              <p className="text-sm text-gray-600">Austin / 🌐 Cloud | Cratejoy</p>
            </div>
            
            <div className="mt-4 md:mt-0">
              <a href="#" className="text-xs text-linkedin-blue hover:underline">Contact info</a>
            </div>
          </motion.div>
          
          {/* Key Metrics */}
          <motion.div 
            className="flex flex-wrap gap-3 mt-6 text-sm"
            initial={{ y: 20, opacity: 0 }}
            animate={{ y: 0, opacity: 1 }}
            transition={{ duration: 0.5, delay: 0.5 }}
          >
            <div className="bg-linkedin-gray rounded-full px-3 py-1">
              🤝 2,500+ Founder Connections
            </div>
            <div className="bg-linkedin-gray rounded-full px-3 py-1">
              🏆 70% Tickets Deleted
            </div>
            <div className="bg-linkedin-gray rounded-full px-3 py-1">
              🚀 $18M GMV Influenced
            </div>
          </motion.div>
          
          {/* Tagline */}
          <motion.p 
            className="mt-6 text-gray-700 max-w-2xl"
            initial={{ y: 20, opacity: 0 }}
            animate={{ y: 0, opacity: 1 }}
            transition={{ duration: 0.5, delay: 0.6 }}
          >
            The first teammate who costs less than software and works as hard as you do.
          </motion.p>
          
          {/* Action Buttons */}
          <motion.div 
            className="mt-6 flex flex-col sm:flex-row sm:items-center gap-3 w-full"
            initial={{ y: 20, opacity: 0 }}
            animate={{ y: 0, opacity: 1 }}
            transition={{ duration: 0.5, delay: 0.7 }}
          >
            <Button 
              onClick={openChat}
              className="bg-cratejoy-teal hover:bg-cratejoy-dark text-white font-medium py-2 px-4 rounded-full flex items-center justify-center w-full sm:w-auto"
            >
              <svg xmlns="http://www.w3.org/2000/svg" className="h-5 w-5 mr-2" viewBox="0 0 20 20" fill="currentColor">
                <path fillRule="evenodd" d="M18 10c0 3.866-3.582 7-8 7a8.841 8.841 0 01-4.083-.98L2 17l1.338-3.123C2.493 12.767 2 11.434 2 10c0-3.866 3.582-7 8-7s8 3.134 8 7zM7 9H5v2h2V9zm8 0h-2v2h2V9zM9 9h2v2H9V9z" clipRule="evenodd" />
              </svg>
              Test-Drive CJ (AI)
            </Button>
            
            <Button 
              onClick={handleDownloadResume}
              variant="outline"
              className="bg-white border border-linkedin-border hover:bg-linkedin-gray text-dark font-medium py-2 px-4 rounded-full flex items-center justify-center w-full sm:w-auto"
            >
              <svg xmlns="http://www.w3.org/2000/svg" className="h-5 w-5 mr-2" viewBox="0 0 20 20" fill="currentColor">
                <path fillRule="evenodd" d="M3 17a1 1 0 011-1h12a1 1 0 110 2H4a1 1 0 01-1-1zm3.293-7.707a1 1 0 011.414 0L9 10.586V3a1 1 0 112 0v7.586l1.293-1.293a1 1 0 111.414 1.414l-3 3a1 1 0 01-1.414 0l-3-3a1 1 0 010-1.414z" clipRule="evenodd" />
              </svg>
              Download Résumé PDF
            </Button>
            
            <p className="text-xs italic text-gray-700 mt-1 sm:mt-0">Yep, even AI needs a résumé. Spoiler: zero job-hops.</p>
          </motion.div>
        </div>
      </div>
    </section>
  );
};

export default Hero;
