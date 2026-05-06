export function Footer() {
  return (
    <footer className="py-4 text-center text-xs text-gray-500 bg-white border-t border-gray-200 shrink-0">
      <p>Data sourced from Groww.in. This tool is for informational purposes only.</p>
      <div className="mt-1 flex justify-center gap-4">
        <a href="https://www.amfiindia.com/" target="_blank" rel="noopener noreferrer" className="hover:underline hover:text-blue-600 transition-colors">AMFI Portal</a>
        <a href="https://www.sebi.gov.in/" target="_blank" rel="noopener noreferrer" className="hover:underline hover:text-blue-600 transition-colors">SEBI Guidelines</a>
      </div>
    </footer>
  );
}
