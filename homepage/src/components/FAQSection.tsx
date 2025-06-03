const FAQSection = () => {
  const faqs = [
    {
      question: "Q • How fast can I go live?",
      answer: "A • OAuth once, import brand-voice doc, you're live in <15 min."
    },
    {
      question: "Q • What does CJ cost?",
      answer: "A • Starts at $299/mo (≈ one shift of human support). Scales by value created, not seat count."
    },
    {
      question: "Q • Is my customer data safe?",
      answer: "A • End-to-end encryption, zero-retention on PII outside Cratejoy; SOC-2, GDPR, PCI in place."
    }
  ];

  return (
    <section id="faqs" className="profile-section section-card p-6">
      <h2 className="text-xl font-bold mb-4">FAQs</h2>
      
      <div className="space-y-6">
        {faqs.map((faq, index) => (
          <div key={index}>
            <h3 className="font-medium text-lg">{faq.question}</h3>
            <p className="mt-1 text-gray-700">
              {faq.answer}
            </p>
          </div>
        ))}
      </div>
    </section>
  );
};

export default FAQSection;
