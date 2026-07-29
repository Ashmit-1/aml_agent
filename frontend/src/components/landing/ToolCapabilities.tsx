import {
  Search,
  TrendingUp,
  ShieldAlert,
  BarChart3,
  Database,
  Terminal,
  Brain,
  UserSearch,
} from 'lucide-react';

const TOOLS = [
  {
    name: 'Search Transactions',
    description:
      'Filter by date, amount, currency, location, or account to find specific transactions.',
    icon: Search,
  },
  {
    name: 'High-Value Transactions',
    description:
      'Find transactions above a configurable threshold (default $10K) to identify large transfers.',
    icon: TrendingUp,
  },
  {
    name: 'Suspicious Patterns',
    description:
      'Analyse flagged laundering transactions to uncover hidden patterns and connections.',
    icon: ShieldAlert,
  },
  {
    name: 'Summary Statistics',
    description:
      'Get aggregated stats grouped by any dimension — country, currency, account, or time period.',
    icon: BarChart3,
  },
  {
    name: 'SQL Queries',
    description:
      'Run custom SQL with window functions, CTEs, and complex joins directly on the dataset.',
    icon: Database,
  },
  {
    name: 'Python Sandbox',
    description:
      'Execute custom analysis in a secure Python sandbox with pandas, numpy, and more.',
    icon: Terminal,
  },
  {
    name: 'ML Detection',
    description:
      'ML-powered AML detection using binary classifiers and pattern recognition models.',
    icon: Brain,
  },
  {
    name: 'Account Investigation',
    description:
      'Score a specific account for suspicious activity with a detailed risk assessment.',
    icon: UserSearch,
  },
];

export const ToolCapabilities = () => {
  return (
    <section className="py-20 px-4 bg-[#0a0a0a]">
      <div className="max-w-6xl mx-auto space-y-12">
        <div className="text-center space-y-4">
          <h2 className="text-3xl md:text-4xl font-medium">Tool Capabilities</h2>
          <p className="text-gray-400 text-lg max-w-2xl mx-auto">
            The agent has access to a suite of specialized tools for transaction
            analysis, from simple searches to complex machine learning models.
          </p>
        </div>

        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
          {TOOLS.map((tool) => (
            <div
              key={tool.name}
              className="p-6 rounded-lg border border-white/10 bg-black hover:border-white/20 transition-colors"
            >
              <div className="flex items-center gap-3 mb-3">
                <tool.icon size={20} className="text-white" />
                <h3 className="font-medium text-white">{tool.name}</h3>
              </div>
              <p className="text-sm text-gray-400 leading-relaxed">
                {tool.description}
              </p>
            </div>
          ))}
        </div>
      </div>
    </section>
  );
};
