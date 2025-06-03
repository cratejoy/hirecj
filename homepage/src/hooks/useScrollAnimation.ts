import { useEffect } from 'react';

export const useScrollAnimation = () => {
  useEffect(() => {
    const observer = new IntersectionObserver(
      (entries) => {
        entries.forEach((entry) => {
          if (entry.isIntersecting) {
            entry.target.classList.add('is-visible');
          }
        });
      },
      { threshold: 0.1 } // Trigger when at least 10% of the element is visible
    );

    const sections = document.querySelectorAll('.profile-section');
    sections.forEach((section) => {
      if (section.id !== 'hero') {
        // Skip the hero section which is already visible
        observer.observe(section);
      }
    });

    return () => {
      sections.forEach((section) => {
        observer.unobserve(section);
      });
    };
  }, []);
};
