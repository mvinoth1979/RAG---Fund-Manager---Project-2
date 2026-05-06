import { ChatInterface } from "./ChatInterface";

export function MainContainer() {
  return (
    <main className="flex-1 flex flex-col overflow-hidden relative w-full max-w-6xl mx-auto shadow-sm bg-white md:border-x border-gray-200">
      <ChatInterface />
    </main>
  );
}
