import { useState, useRef, useEffect } from "react";
import { WelcomeScreen } from "./WelcomeScreen";
import { MessageList } from "./MessageList";
import { InputArea } from "./InputArea";
import type { Message } from '../types';

export function ChatInterface() {
  const [messages, setMessages] = useState<Message[]>([]);
  const [isLoading, setIsLoading] = useState(false);
  
  const bottomRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    if (bottomRef.current) {
      bottomRef.current.scrollIntoView({ behavior: 'smooth' });
    }
  }, [messages, isLoading]);

  const handleSend = async (query: string) => {
    const userMsg: Message = { id: Date.now().toString(), role: 'user', content: query };
    setMessages(prev => [...prev, userMsg]);
    setIsLoading(true);

    try {
      const apiUrl = import.meta.env.VITE_API_URL || 'http://localhost:8000/api/chat';
      const res = await fetch(apiUrl, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ query })
      });
      
      const data = await res.json();
      
      const isError = res.status !== 200 || data.text.includes("I cannot provide investment advice") || data.text.includes("I'm unable to answer right now");

      const astMsg: Message = {
        id: (Date.now() + 1).toString(),
        role: 'assistant',
        content: data.text,
        source_url: data.source_url,
        last_updated: data.last_updated,
        disclaimer: data.disclaimer,
        isError: isError
      };
      
      setMessages(prev => [...prev, astMsg]);
    } catch (error) {
      const errMsg: Message = {
        id: (Date.now() + 1).toString(),
        role: 'assistant',
        content: "Network error. Make sure the backend API is running.",
        isError: true
      };
      setMessages(prev => [...prev, errMsg]);
    } finally {
      setIsLoading(false);
    }
  };

  return (
    <div className="flex flex-col flex-1 h-full bg-[#f9fafb] overflow-hidden relative">
      {messages.length === 0 ? (
        <div className="flex-1 overflow-y-auto">
          <WelcomeScreen onSelectQuery={handleSend} />
        </div>
      ) : (
        <>
          <MessageList messages={messages} isLoading={isLoading} />
          <div ref={bottomRef} />
        </>
      )}
      
      <div className="mt-auto">
        <InputArea onSend={handleSend} disabled={isLoading} />
      </div>
    </div>
  );
}
