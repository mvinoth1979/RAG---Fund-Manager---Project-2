import { MessageSquare, TrendingUp, HelpCircle } from "lucide-react";

interface WelcomeScreenProps {
  onSelectQuery: (query: string) => void;
}

export function WelcomeScreen({ onSelectQuery }: WelcomeScreenProps) {
  const examples = [
    { text: "What is the expense ratio of the Small Cap Fund?", icon: <TrendingUp className="text-blue-500 mb-2" size={24} /> },
    { text: "What is the exit load for the Liquid Fund?", icon: <HelpCircle className="text-emerald-500 mb-2" size={24} /> },
    { text: "What is the benchmark index for the Flexi Cap Fund?", icon: <MessageSquare className="text-purple-500 mb-2" size={24} /> },
  ];

  return (
    <div className="flex flex-col items-center justify-center h-full px-4 w-full">
      <div className="w-16 h-16 bg-blue-100 rounded-2xl flex items-center justify-center mb-6 shadow-sm">
        <MessageSquare className="text-blue-600" size={32} />
      </div>
      <h2 className="text-2xl font-bold text-gray-800 mb-2 text-center">How can I help you today?</h2>
      <p className="text-gray-500 mb-8 max-w-md text-center">Ask me factual questions about The Wealth Company mutual funds. I extract verified data straight from official sources.</p>
      
      <div className="grid grid-cols-1 md:grid-cols-3 gap-4 w-full max-w-3xl">
        {examples.map((ex, i) => (
          <button 
            key={i} 
            onClick={() => onSelectQuery(ex.text)}
            className="flex flex-col items-center text-center p-6 bg-white border border-gray-200 rounded-xl hover:border-blue-300 hover:shadow-md transition-all active:scale-95 group"
          >
            <div className="group-hover:-translate-y-1 transition-transform">{ex.icon}</div>
            <span className="text-sm font-medium text-gray-700 leading-snug">{ex.text}</span>
          </button>
        ))}
      </div>
    </div>
  );
}
