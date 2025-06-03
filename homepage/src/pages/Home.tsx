import { useState, useEffect } from 'react';
import { Link, useLocation } from 'wouter';
import Hero from '@/components/Hero';
import AboutSection from '@/components/AboutSection';
import ExperienceSection from '@/components/ExperienceSection';
import SkillsSection from '@/components/SkillsSection';
import CertificationsSection from '@/components/CertificationsSection';
import RecommendationsSection from '@/components/RecommendationsSection';
import WhatIDoSection from '@/components/WhatIDoSection';
import FAQSection from '@/components/FAQSection';
import CTASection from '@/components/CTASection';
import Footer from '@/components/Footer';
import ChatPill from '@/components/ChatPill';
import EmailCaptureModal from '@/components/EmailCaptureModal';
import { useScrollAnimation } from '@/hooks/useScrollAnimation';
import { useChat } from '@/hooks/useChat';
import { Helmet } from 'react-helmet';

const Home = () => {
  const [, setLocation] = useLocation();
  const [isEmailModalOpen, setIsEmailModalOpen] = useState(false);
  const [showChatPill, setShowChatPill] = useState(false);
  const [showBanner, setShowBanner] = useState(true);
  const [bannerVisible, setBannerVisible] = useState(true);
  
  const { 
    captureEmail 
  } = useChat(setIsEmailModalOpen);
  
  useScrollAnimation();
  
  // Navigate to chat
  const navigateToChat = () => {
    setLocation('/chat');
  };
  
  // Handle scroll effects: chat pill visibility and auto-hiding banner
  useEffect(() => {
    const handleScroll = () => {
      const scrollY = window.scrollY;
      const isAtTop = scrollY < 200;
      const isMobile = window.innerWidth < 768;
      
      // Auto-hide banner after scrolling down
      if (scrollY > 300) {
        setBannerVisible(false);
      } else {
        setBannerVisible(true);
      }
      
      // Get main CTA element position
      const heroSection = document.getElementById('hero');
      
      // For desktop: always show the chat pill except at the very top of the page
      if (!isMobile) {
        setShowChatPill(!isAtTop);
        return;
      }
      
      // For mobile: only show chat pill when scrolled past hero section
      if (heroSection && isMobile) {
        const heroRect = heroSection.getBoundingClientRect();
        const isHeroVisible = heroRect.bottom > 0;
        setShowChatPill(!isHeroVisible);
      }
    };
    
    // Show chat pill after a short delay on desktop
    const timer = setTimeout(() => {
      if (window.innerWidth >= 768) {
        setShowChatPill(true);
      }
    }, 2000);
    
    window.addEventListener('scroll', handleScroll);
    // Trigger once to set initial state
    handleScroll();
    
    return () => {
      window.removeEventListener('scroll', handleScroll);
      clearTimeout(timer);
    };
  }, []);
  
  // Keyboard shortcuts
  useEffect(() => {
    const handleKeyDown = (e: KeyboardEvent) => {
      // Press 'C' to open chat (but not with modifier keys like Cmd+C for copy)
      if (e.key === 'c' && 
          !(e.target instanceof HTMLInputElement) && 
          !e.metaKey && 
          !e.ctrlKey && 
          !e.altKey && 
          !e.shiftKey) {
        navigateToChat();
      }
      
      // ESC key to close email modal
      if (e.key === 'Escape') {
        setIsEmailModalOpen(false);
      }
    };
    
    window.addEventListener('keydown', handleKeyDown);
    return () => window.removeEventListener('keydown', handleKeyDown);
  }, []);
  
  return (
    <>
      <Helmet>
        <title>Hire CJ - Autonomous CX & Growth Officer</title>
        <meta name="description" content="The first AI teammate who costs less than software and works harder than you do. Delete busywork, compound LTV, and make 'out of office' a reality again." />
      </Helmet>
      
      <div className="min-h-screen bg-linkedin-gray overflow-y-auto">
        {/* Micro Banner - auto-hides on scroll */}
        {showBanner && (
          <div className={`w-full bg-cratejoy-teal py-2 sm:py-1.5 text-center fixed top-0 left-0 right-0 z-[1000] transition-all duration-300 ${bannerVisible ? 'opacity-100' : 'opacity-0 -translate-y-full'}`} style={{ minHeight: '28px' }}>
            <div className="relative max-w-6xl mx-auto">
              <p className="text-white text-xs font-semibold px-4 leading-relaxed">
                ⚡ This résumé belongs to an AI coworker you can hire today — chat to see her work.
              </p>
            </div>
          </div>
        )}
        
        {/* Removed header with HireCJ logo since we have the banner */}
        
        {/* Main content with top padding for banner */}
        <div className="container mx-auto px-4 pb-6 max-w-4xl pt-[40px]">
          <Hero openChat={navigateToChat} />
          <AboutSection />
          <ExperienceSection />
          <SkillsSection />
          <CertificationsSection />
          <RecommendationsSection />
          <WhatIDoSection />
          <FAQSection />
          <CTASection openChat={navigateToChat} />
          <Footer />
        </div>
        
        {/* Floating chat button */}
        {showChatPill && (
          <ChatPill onClick={navigateToChat} />
        )}
        
        {/* Email capture modal */}
        <EmailCaptureModal 
          isOpen={isEmailModalOpen} 
          onClose={() => setIsEmailModalOpen(false)}
          onSubmit={captureEmail}
        />
      </div>
    </>
  );
};

export default Home;
