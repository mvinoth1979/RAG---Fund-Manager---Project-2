import ReactMarkdown from 'react-markdown';
import { User, Bot, Ban } from 'lucide-react';
import type { Message } from '../types';

export function MessageList({ messages, isLoading }: { messages: Message[], isLoading: boolean }) {
  return (
    <div className="flex-1 overflow-y-auto p-4 md:p-6 space-y-6 w-full max-w-4xl mx-auto scroll-smooth">
      {messages.map((msg) => (
        <div key={msg.id} className={`flex gap-3 md:gap-4 ${msg.role === 'user' ? 'flex-row-reverse' : ''}`}>
          <div className={`shrink-0 w-8 h-8 md:w-10 md:h-10 rounded-full flex items-center justify-center shadow-sm ${msg.role === 'user' ? 'bg-blue-600 text-white' : (msg.isError ? 'bg-red-100 text-red-600' : 'bg-gray-800 text-white')}`}>
            {msg.role === 'user' ? <User size={20} /> : (msg.isError ? <Ban size={20} /> : <Bot size={20} />)}
          </div>
          
          <div className={`flex flex-col max-w-[85%] ${msg.role === 'user' ? 'items-end' : 'items-start'}`}>
            <div className={`px-4 md:px-5 py-3 md:py-3.5 rounded-2xl shadow-sm text-sm md:text-base ${
              msg.role === 'user' 
                ? 'bg-blue-600 text-white rounded-tr-sm' 
                : (msg.isError ? 'bg-red-50 border border-red-100 text-red-900 rounded-tl-sm' : 'bg-white border border-gray-100 text-gray-800 rounded-tl-sm')
            }`}>
              {msg.role === 'assistant' ? (
                <div className="prose prose-sm md:prose-base prose-a:text-blue-600 hover:prose-a:underline break-words">
                  <ReactMarkdown>{msg.content}</ReactMarkdown>
                </div>
              ) : (
                <p className="whitespace-pre-wrap break-words">{msg.content}</p>
              )}
            </div>
            
            {msg.role === 'assistant' && (
              <div className="mt-2 text-xs text-gray-400 space-y-1 pl-2">
                {msg.source_url && (
                  <div className="flex items-center gap-1">
                    <span className="font-medium text-gray-500">Source:</span>
                    {msg.source_url === 'N/A' ? (
                      <span>N/A</span>
                    ) : (
                      <a href={msg.source_url} target="_blank" rel="noopener noreferrer" className="text-blue-500 hover:underline truncate max-w-[200px] md:max-w-md inline-block align-bottom">
                        {new URL(msg.source_url).hostname + new URL(msg.source_url).pathname}
                      </a>
                    )}
                  </div>
                )}
                {msg.last_updated && <p>Last updated: {msg.last_updated}</p>}
                {msg.disclaimer && <p className="text-amber-600/80 italic mt-1">{msg.disclaimer}</p>}
              </div>
            )}
          </div>
        </div>
      ))}
      {isLoading && (
        <div className="flex gap-4">
          <div className="shrink-0 w-10 h-10 bg-gray-800 text-white rounded-full flex items-center justify-center">
            <Bot size={20} className="animate-pulse" />
          </div>
          <div className="bg-white border border-gray-100 px-5 py-4 rounded-2xl rounded-tl-sm shadow-sm flex items-center gap-1">
            <div className="w-2 h-2 bg-gray-400 rounded-full animate-bounce [animation-delay:-0.3s]"></div>
            <div className="w-2 h-2 bg-gray-400 rounded-full animate-bounce [animation-delay:-0.15s]"></div>
            <div className="w-2 h-2 bg-gray-400 rounded-full animate-bounce"></div>
          </div>
        </div>
      )}
    </div>
  );
}
