export const AboutSection = () => {
  return (
    <section className="py-20 px-4">
      <div className="max-w-4xl mx-auto text-center space-y-6">
        <h2 className="text-3xl md:text-4xl font-medium">About the Agent</h2>
        <p className="text-gray-400 text-lg leading-relaxed">
          A powerful AI agent built to analyze massive datasets of bank
          transactions. It uses advanced language models and specialized tools
          to identify suspicious patterns that may indicate money laundering
          activity.
        </p>
        <div className="flex flex-wrap justify-center gap-4 pt-4">
          {['LangGraph', 'FastAPI', 'DuckDB', 'Gemma 4'].map((tech) => (
            <span
              key={tech}
              className="px-4 py-2 rounded-md border border-white/10 text-sm text-gray-300"
            >
              {tech}
            </span>
          ))}
        </div>
      </div>
    </section>
  );
};
