import { Button } from '@/components/ui/button';

interface CTASectionProps {
  openChat: () => void;
}

const CTASection: React.FC<CTASectionProps> = ({ openChat }) => {
  return (
    <section id="cta" className="profile-section bg-gradient-to-r from-cratejoy-teal to-linkedin-blue rounded-lg shadow-lg p-8 mb-5 text-center">
      <h2 className="text-2xl font-bold text-white mb-4">Ready to delete busy-work and make more money?</h2>
      <Button 
        onClick={openChat}
        className="bg-white text-cratejoy-teal hover:bg-gray-100 font-medium py-3 px-8 rounded-full text-lg inline-flex items-center"
      >
        <svg xmlns="http://www.w3.org/2000/svg" className="h-6 w-6 mr-2" viewBox="0 0 20 20" fill="currentColor">
          <path fillRule="evenodd" d="M18 10c0 3.866-3.582 7-8 7a8.841 8.841 0 01-4.083-.98L2 17l1.338-3.123C2.493 12.767 2 11.434 2 10c0-3.866 3.582-7 8-7s8 3.134 8 7zM7 9H5v2h2V9zm8 0h-2v2h2V9zM9 9h2v2H9V9z" clipRule="evenodd" />
        </svg>
        Chat with CJ Now
      </Button>
    </section>
  );
};

export default CTASection;
