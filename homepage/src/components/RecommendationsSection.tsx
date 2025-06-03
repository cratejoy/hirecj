const RecommendationsSection = () => {
  const recommendations = [
    {
      name: "Alexis B.",
      role: "Founder @ Escape-the-Crate",
      quote: "CJ gave me my weekends back. We're pocketing ~$6k/mo she used to cost in headcount.",
      avatar: "https://images.unsplash.com/photo-1573496359142-b8d87734a5a2?ixlib=rb-4.0.3&ixid=MnwxMjA3fDB8MHxwaG90by1wYWdlfHx8fGVufDB8fHx8&auto=format&fit=crop&w=48&h=48"
    },
    {
      name: "Sean S.",
      role: "CMO @ Iron Neck",
      quote: "Support cost down 58%, upsell GMV up 12%—all inside a month.",
      avatar: "https://images.unsplash.com/photo-1507003211169-0a1dd7228f2d?ixlib=rb-4.0.3&ixid=MnwxMjA3fDB8MHxwaG90by1wYWdlfHx8fGVufDB8fHx8&auto=format&fit=crop&w=48&h=48"
    },
    {
      name: "Amir Elaguizy",
      role: "CEO of CJ",
      quote: "CJ is the teammate we'd hire twice if she needed sleep—she doesn't.",
      avatar: "https://images.unsplash.com/photo-1507003211169-0a1dd7228f2d?ixlib=rb-4.0.3&ixid=MnwxMjA3fDB8MHxwaG90by1wYWdlfHx8fGVufDB8fHx8&auto=format&fit=crop&w=48&h=48"
    }
  ];

  return (
    <section id="recommendations" className="profile-section section-card p-6">
      <h2 className="text-xl font-bold mb-4">Featured Recommendations</h2>
      
      <div className="space-y-6">
        {recommendations.map((rec, index) => (
          <div 
            key={index} 
            className={index < recommendations.length - 1 ? "border-b border-linkedin-border pb-6" : ""}
          >
            <div className="flex items-start">
              <div className="mr-4">
                <img 
                  src={rec.avatar} 
                  alt={`${rec.name} profile`} 
                  className="h-12 w-12 object-cover rounded-full"
                />
              </div>
              <div>
                <h3 className="font-medium">{rec.name}</h3>
                <p className="text-sm text-gray-600">{rec.role}</p>
                <p className="mt-2 text-gray-700">"{rec.quote}"</p>
              </div>
            </div>
          </div>
        ))}
      </div>
    </section>
  );
};

export default RecommendationsSection;
