import { ShieldAlert } from "lucide-react";

export function Header() {
  return (
    <header className="h-14 md:h-16 flex items-center justify-between px-4 md:px-6 bg-white border-b border-gray-200 shrink-0 shadow-sm sticky top-0 z-10">
      <h1 className="font-semibold text-lg text-gray-800">Mutual Fund FAQ Assistant</h1>
      <div className="flex items-center gap-2 bg-amber-50 text-amber-800 text-xs md:text-sm px-3 py-1.5 rounded-full font-medium border border-amber-200">
        <ShieldAlert size={16} />
        <span className="hidden sm:inline">Not Investment Advice</span>
      </div>
    </header>
  );
}
