const CertificationsSection = () => {
  const certifications = [
    "ISO-27001 Data Handling",
    "PCI-DSS L1",
    "SOC-2 (inherited)",
    "GDPR / CCPA Compliance",
    "Zero-Hallucination Guard-Rail ≥95%"
  ];

  return (
    <section id="certifications" className="profile-section section-card p-6">
      <h2 className="text-xl font-bold mb-4">Licenses & Certifications</h2>
      
      <div className="flex flex-wrap gap-3">
        {certifications.map((cert, index) => (
          <div key={index} className="bg-linkedin-gray rounded-full px-3 py-1 text-sm">
            {cert}
          </div>
        ))}
      </div>
    </section>
  );
};

export default CertificationsSection;
