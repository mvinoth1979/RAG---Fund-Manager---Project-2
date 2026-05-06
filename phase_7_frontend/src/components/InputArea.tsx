import { useState, FormEvent } from "react";
import { SendHorizontal } from "lucide-react";

interface InputAreaProps {
  onSend: (query: string) => void;
  disabled: boolean;
}

export function InputArea({ onSend, disabled }: InputAreaProps) {
  const [input, setInput] = useState("");

  const handleSubmit = (e: FormEvent) => {
    e.preventDefault();
    if (input.trim() && !disabled) {
      onSend(input.trim());
      setInput("");
    }
  };

  return (
    <div className="p-4 bg-white border-t border-gray-200 shrink-0">
      <form onSubmit={handleSubmit} className="max-w-4xl mx-auto relative flex items-center">
        <input
          type="text"
          value={input}
          onChange={(e) => setInput(e.target.value.slice(0, 200))}
          disabled={disabled}
          placeholder="Ask a question about a mutual fund..."
          className="w-full bg-gray-50 border border-gray-300 rounded-full pl-5 pr-14 py-3.5 focus:outline-none focus:ring-2 focus:ring-blue-500/50 focus:border-blue-500 transition-shadow disabled:opacity-50 text-gray-800 shadow-inner"
        />
        <button
          type="submit"
          disabled={!input.trim() || disabled}
          className="absolute right-2 top-1/2 -translate-y-1/2 p-2 bg-blue-600 text-white rounded-full hover:bg-blue-700 disabled:opacity-50 disabled:hover:bg-blue-600 transition-colors shadow-sm active:scale-95"
        >
          <SendHorizontal size={20} />
        </button>
      </form>
      <div className="text-center mt-2 text-[10px] text-gray-400">
        {input.length}/200 characters
      </div>
    </div>
  );
}
