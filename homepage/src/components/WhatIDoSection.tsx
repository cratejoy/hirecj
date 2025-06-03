const WhatIDoSection = () => {
  const services = [
    {
      title: "Support Autopilot",
      description: "Kill 70% of inbox noise, answer 24/7, keep CSAT >4.8★",
      icon: "headset"
    },
    {
      title: "Reputation Rescue",
      description: "Reply to every review, flip bad ones before they bite conversions",
      icon: "star-half-alt"
    },
    {
      title: "Concierge Engine",
      description: "Segment every shopper, upsell whales, save churn-risk subs",
      icon: "concierge-bell"
    },
    {
      title: "Content Optimizer",
      description: "Generate & A/B test PDP + email copy that sells while you sleep",
      icon: "pen-fancy"
    },
    {
      title: "Insight Feed",
      description: "Weekly brief surfaces supply-chain issues, product gaps & promo angles",
      icon: "lightbulb"
    }
  ];

  return (
    <section id="what-i-do" className="profile-section section-card p-6">
      <h2 className="text-xl font-bold mb-4">What I Do For You</h2>
      
      <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
        {services.map((service, index) => (
          <div 
            key={index} 
            className={index === 4 ? "md:col-span-2 border border-linkedin-border rounded-lg p-4 hover:shadow-md transition duration-300" : "border border-linkedin-border rounded-lg p-4 hover:shadow-md transition duration-300"}
          >
            <h3 className="font-medium text-lg text-cratejoy-teal">{service.title}</h3>
            <p className="mt-2 text-gray-700">
              {service.description}
            </p>
          </div>
        ))}
      </div>
    </section>
  );
};

export default WhatIDoSection;
