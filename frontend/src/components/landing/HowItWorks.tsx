import { MessageSquare, Cpu, Eye, FileText } from 'lucide-react';

const STEPS = [
  {
    step: 1,
    title: 'Ask a Question',
    description:
      'Type your question in natural language — no SQL or code required.',
    icon: MessageSquare,
  },
  {
    step: 2,
    title: 'Agent Plans & Calls Tools',
    description:
      'The agent breaks down your question and selects the right tools to gather data.',
    icon: Cpu,
  },
  {
    step: 3,
    title: 'See Real-Time Progress',
    description:
      'Watch the agent think, call tools, and process results in real time.',
    icon: Eye,
  },
  {
    step: 4,
    title: 'Get the Answer',
    description:
      'Receive a well-formatted answer with Markdown, charts, and code blocks.',
    icon: FileText,
  },
];

export const HowItWorks = () => {
  return (
    <section className="py-20 px-4">
      <div className="max-w-4xl mx-auto space-y-12">
        <div className="text-center space-y-4">
          <h2 className="text-3xl md:text-4xl font-medium">How It Works</h2>
          <p className="text-gray-400 text-lg">
            From question to insight in four simple steps.
          </p>
        </div>

        <div className="grid grid-cols-1 md:grid-cols-2 gap-8">
          {STEPS.map((step) => (
            <div key={step.step} className="flex gap-4">
              <div className="flex-shrink-0 h-10 w-10 rounded-full border border-white flex items-center justify-center">
                <step.icon size={18} />
              </div>
              <div className="space-y-2">
                <h3 className="font-medium text-white">
                  Step {step.step}: {step.title}
                </h3>
                <p className="text-sm text-gray-400 leading-relaxed">
                  {step.description}
                </p>
              </div>
            </div>
          ))}
        </div>
      </div>
    </section>
  );
};
