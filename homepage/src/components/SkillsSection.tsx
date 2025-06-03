import { motion } from 'framer-motion';

const SkillsSection = () => {
  const skills = [
    {
      name: "Sentiment Mapping",
      endorsements: "1,973 endorsements",
      description: "Automatically categorizes customer emotions and intent to prioritize responses and identify trends."
    },
    {
      name: "Order-API Orchestration",
      endorsements: "1,458 endorsements",
      description: "Connects shipping, inventory, and payment systems to resolve issues without human intervention."
    },
    {
      name: "Brand-Voice Mimicry",
      endorsements: "98% match rate",
      description: "Adopts your brand's tone and voice so customers can't tell they're talking to an AI."
    },
    {
      name: "A/B Copy Alchemy",
      endorsements: "1,209 endorsements",
      description: "Generates and tests product descriptions that convert higher based on customer feedback data."
    }
  ];
  
  const minorSkills = [
    "Churn Prediction & Saves",
    "Concierge Upsells",
    "SQL & Stream Processing"
  ];

  return (
    <section id="skills" className="profile-section section-card p-6">
      <h2 className="text-xl font-bold mb-4">Skills & Endorsements</h2>
      
      <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
        {skills.map((skill, index) => (
          <motion.div 
            key={index}
            className="skill-badge bg-linkedin-gray rounded-lg p-4 cursor-pointer"
            whileHover={{ y: -5, backgroundColor: "rgba(231, 243, 255, 1)" }}
            transition={{ duration: 0.2 }}
          >
            <div className="flex justify-between items-center">
              <h3 className="font-medium">{skill.name}</h3>
              <span className="text-sm text-linkedin-dark-gray">{skill.endorsements}</span>
            </div>
            <div className="mt-2 bg-white rounded-md p-3 text-sm">
              <p>{skill.description}</p>
            </div>
          </motion.div>
        ))}
      </div>
      
      <div className="mt-4 grid grid-cols-1 md:grid-cols-3 gap-4">
        {minorSkills.map((skill, index) => (
          <motion.div 
            key={index}
            className="skill-badge bg-linkedin-gray rounded-lg p-3 cursor-pointer"
            whileHover={{ y: -5, backgroundColor: "rgba(231, 243, 255, 1)" }}
            transition={{ duration: 0.2 }}
          >
            <h3 className="font-medium">{skill}</h3>
          </motion.div>
        ))}
      </div>
    </section>
  );
};

export default SkillsSection;
