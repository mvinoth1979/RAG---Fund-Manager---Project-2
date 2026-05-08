import React, { useState, useRef, useEffect } from 'react';
import { Send, Shield, Info, ExternalLink, ChevronRight, PieChart, TrendingUp, Lock } from 'lucide-react';
import ReactMarkdown from 'react-markdown';

// --- Types ---
interface Message {
  id: string;
  type: 'user' | 'assistant';
  content: string;
  timestamp: Date;
  isAnalyzing?: boolean;
  sources?: string[];
}

// --- Components ---

const MessageBubble = ({ message }: { message: Message }) => {
  const isAssistant = message.type === 'assistant';

  return (
    <div className={`flex w-full mb-6 ${isAssistant ? 'justify-start' : 'justify-end'} animate-fade-in`}>
      <div className={`relative max-w-[85%] rounded-2xl p-5 ${
        isAssistant 
          ? 'glass-surface border-l-4 border-l-accent-growth text-on-surface' 
          : 'bg-brand-navy text-white shadow-lg'
      }`}>
        {message.isAnalyzing ? (
          <div className="flex items-center space-x-3 py-2">
            <div className="flex space-x-1">
              <div className="w-2 h-2 bg-accent-growth rounded-full animate-bounce" style={{ animationDelay: '0ms' }}></div>
              <div className="w-2 h-2 bg-accent-growth rounded-full animate-bounce" style={{ animationDelay: '150ms' }}></div>
              <div className="w-2 h-2 bg-accent-growth rounded-full animate-bounce" style={{ animationDelay: '300ms' }}></div>
            </div>
            <span className="text-sm font-medium text-on-surface-variant">Analyzing official sources...</span>
          </div>
        ) : (
          <>
            <div className="prose prose-sm max-w-none">
              <ReactMarkdown>{message.content}</ReactMarkdown>
            </div>
            {message.sources && message.sources.length > 0 && (
              <div className="mt-4 pt-4 border-t border-outline-variant/30">
                <p className="text-[10px] uppercase tracking-wider font-bold text-on-surface-variant mb-2">Verified Sources</p>
                <div className="flex flex-wrap gap-2">
                  {message.sources.map((source, idx) => (
                    <a 
                      key={idx}
                      href={source}
                      target="_blank"
                      rel="noopener noreferrer"
                      className="inline-flex items-center px-2 py-1 bg-surface-container-low rounded-md text-[11px] text-brand-navy hover:bg-surface-container-high transition-colors border border-outline-variant/20"
                    >
                      Source {idx + 1} <ExternalLink size={10} className="ml-1" />
                    </a>
                  ))}
                </div>
              </div>
            )}
          </>
        )}
      </div>
    </div>
  );
};

const QuickAction = ({ icon: Icon, label, onClick }: { icon: any, label: string, onClick: () => void }) => (
  <button 
    onClick={onClick}
    className="flex items-center p-4 bg-white hover:bg-surface-container-low border border-outline-variant/20 rounded-xl transition-all hover:premium-shadow group w-full text-left"
  >
    <div className="p-2 bg-surface-container-highest rounded-lg mr-4 group-hover:bg-accent-growth/10 transition-colors">
      <Icon size={20} className="text-brand-navy group-hover:text-accent-growth transition-colors" />
    </div>
    <span className="font-medium text-on-surface">{label}</span>
    <ChevronRight size={16} className="ml-auto text-outline" />
  </button>
);

const ComplianceBanner = () => (
  <div className="bg-surface-container-low/80 backdrop-blur-md border-t border-outline-variant/30 py-3 px-6">
    <div className="max-w-screen-lg mx-auto flex items-center justify-between">
      <div className="flex items-center space-x-3">
        <Shield size={16} className="text-secondary" />
        <p className="text-[11px] text-on-surface-variant leading-tight max-w-2xl">
          <strong>SEC/FINRA COMPLIANT:</strong> This AI assistant provides factual information from official mutual fund prospectuses. It does not provide investment advice, guarantees, or personalized recommendations. Past performance is not indicative of future results.
        </p>
      </div>
      <button className="text-[11px] font-bold text-brand-navy hover:underline whitespace-nowrap ml-4">VIEW FULL DISCLAIMER</button>
    </div>
  </div>
);

// --- Main App ---

export default function App() {
  const [messages, setMessages] = useState<Message[]>([]);
  const [input, setInput] = useState('');
  const [isTyping, setIsTyping] = useState(false);
  const scrollRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    if (scrollRef.current) {
      scrollRef.current.scrollTop = scrollRef.current.scrollHeight;
    }
  }, [messages]);

  const handleSend = async (text: string = input) => {
    if (!text.trim()) return;

    const userMessage: Message = {
      id: Date.now().toString(),
      type: 'user',
      content: text,
      timestamp: new Date(),
    };

    setMessages(prev => [...prev, userMessage]);
    setInput('');
    setIsTyping(true);

    // Mock analyzing state
    const analyzingId = (Date.now() + 1).toString();
    setMessages(prev => [...prev, {
      id: analyzingId,
      type: 'assistant',
      content: '',
      timestamp: new Date(),
      isAnalyzing: true
    }]);

    // Simulate API call
    setTimeout(() => {
      setMessages(prev => prev.filter(m => m.id !== analyzingId).concat({
        id: analyzingId,
        type: 'assistant',
        content: "Based on the official fund prospectus, the **Wealth Company Small Cap Fund** currently holds a net asset value (NAV) of ₹124.50. The fund maintains a 65% allocation in equity and equity-related instruments of small-cap companies to ensure regulatory compliance.",
        timestamp: new Date(),
        sources: ["https://groww.in/mutual-funds/the-wealth-company-small-cap-fund-direct-growth"]
      }));
      setIsTyping(false);
    }, 2000);
  };

  return (
    <div className="flex flex-col h-screen bg-surface selection:bg-accent-growth/20">
      {/* Header */}
      <header className="glass-surface border-b border-outline-variant/30 py-4 px-6 z-10">
        <div className="max-w-screen-lg mx-auto flex items-center justify-between">
          <div className="flex items-center space-x-3">
            <div className="w-10 h-10 bg-brand-navy rounded-xl flex items-center justify-center premium-shadow">
              < TrendingUp className="text-white" size={20} />
            </div>
            <div>
              <h1 className="text-xl leading-none">WealthWise AI</h1>
              <p className="text-[10px] text-on-surface-variant font-bold uppercase tracking-widest mt-1">Institutional Grade RAG</p>
            </div>
          </div>
          <div className="hidden md:flex items-center space-x-6">
            <nav className="flex space-x-4 text-sm font-medium">
              <a href="#" className="text-brand-navy border-b-2 border-accent-growth pb-1">Chat</a>
              <a href="#" className="text-on-surface-variant hover:text-brand-navy transition-colors">Funds</a>
              <a href="#" className="text-on-surface-variant hover:text-brand-navy transition-colors">Compliance</a>
            </nav>
            <button className="bg-brand-navy text-white text-xs font-bold px-4 py-2 rounded-lg hover:bg-black transition-colors">LOGIN</button>
            <div className="flex items-center px-3 py-1 bg-secondary/10 rounded-full border border-secondary/20">
              <div className="w-1.5 h-1.5 bg-secondary rounded-full mr-2 animate-pulse"></div>
              <span className="text-[10px] font-bold text-secondary uppercase tracking-tight">System Secure</span>
            </div>
          </div>
        </div>
      </header>

      {/* Main Content */}
      <main className="flex-1 overflow-hidden relative flex flex-col">
        <div 
          ref={scrollRef}
          className="flex-1 overflow-y-auto px-6 py-8 scroll-smooth"
        >
          <div className="chat-container">
            {messages.length === 0 ? (
              <div className="max-w-xl mx-auto mt-12 text-center animate-fade-in">
                <div className="mb-8 inline-flex p-4 bg-surface-container-low rounded-3xl premium-shadow">
                  <PieChart size={48} className="text-brand-navy" />
                </div>
                <h2 className="text-4xl mb-4 leading-tight">Secure Financial Intelligence</h2>
                <p className="text-lg text-on-surface-variant mb-12">
                  Access real-time, verified mutual fund data through our institutional-grade retrieval engine.
                </p>
                
                <div className="grid gap-4">
                  <QuickAction 
                    icon={TrendingUp} 
                    label="Explain Small Cap Fund Performance" 
                    onClick={() => handleSend("Tell me about the Wealth Company Small Cap Fund performance")}
                  />
                  <QuickAction 
                    icon={Info} 
                    label="What are the latest NAV updates?" 
                    onClick={() => handleSend("Show me the latest NAV for all funds")}
                  />
                  <QuickAction 
                    icon={Lock} 
                    label="Verify Fund Compliance Status" 
                    onClick={() => handleSend("Is the Ethical Fund compliant with latest regulations?")}
                  />
                </div>

                <div className="mt-12 flex items-center justify-center space-x-6 grayscale opacity-50">
                  <span className="text-[10px] font-bold tracking-widest uppercase">Verified by</span>
                  <div className="h-4 w-20 bg-on-surface-variant/20 rounded"></div>
                  <div className="h-4 w-24 bg-on-surface-variant/20 rounded"></div>
                  <div className="h-4 w-16 bg-on-surface-variant/20 rounded"></div>
                </div>
              </div>
            ) : (
              messages.map(m => <MessageBubble key={m.id} message={m} />)
            )}
          </div>
        </div>

        {/* Input Area */}
        <div className="bg-gradient-to-t from-surface via-surface to-transparent pt-12 pb-6 px-6">
          <div className="chat-container relative">
            <div className={`glass-surface rounded-2xl flex items-center p-2 transition-all duration-300 ${isTyping ? 'premium-shadow ring-2 ring-accent-growth/20' : 'hover:premium-shadow'}`}>
              <div className="flex-1 px-4 py-2">
                <input 
                  type="text"
                  placeholder="Ask about funds, NAV, or compliance..."
                  className="w-full bg-transparent border-none focus:ring-0 text-on-surface placeholder:text-outline py-2"
                  value={input}
                  onChange={(e) => setInput(e.target.value)}
                  onKeyPress={(e) => e.key === 'Enter' && handleSend()}
                />
              </div>
              <button 
                onClick={() => handleSend()}
                disabled={!input.trim() && !isTyping}
                className={`p-3 rounded-xl transition-all ${
                  input.trim() 
                    ? 'bg-accent-growth text-white hover:scale-105 active:scale-95' 
                    : 'bg-surface-container text-outline'
                }`}
              >
                <Send size={20} />
              </button>
            </div>
            <p className="text-[10px] text-center mt-4 text-on-surface-variant font-medium">
              Enterprise RAG v4.2 • Secure Session • Zero-Retention Policy
            </p>
          </div>
        </div>
      </main>

      <ComplianceBanner />
    </div>
  );
}
