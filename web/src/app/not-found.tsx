export default function NotFound() {
  return (
    <div className="min-h-screen bg-zinc-950 text-zinc-100 flex items-center justify-center">
      <div className="text-center">
        <h1 className="text-6xl font-bold text-zinc-700 mb-4">404</h1>
        <p className="text-xl text-zinc-400 mb-6">Page not found</p>
        <a
          href="/chat"
          className="inline-block px-5 py-2.5 bg-blue-600 hover:bg-blue-500 text-white rounded-lg transition-colors text-sm font-medium"
        >
          Back to Jarvis
        </a>
      </div>
    </div>
  );
}
