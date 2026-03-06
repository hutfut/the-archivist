function App() {
  return (
    <div className="grid grid-cols-[320px_1fr] h-screen overflow-hidden">
      <aside className="flex flex-col p-6 overflow-y-auto border-r border-gray-200 bg-gray-50 dark:border-gray-700 dark:bg-gray-900">
        <h2 className="text-lg font-semibold mb-3">Documents</h2>
        <p className="text-gray-500 text-sm">Upload and manage documents here.</p>
      </aside>
      <main className="flex flex-col overflow-y-auto bg-white dark:bg-gray-800">
        <h2 className="text-lg font-semibold p-6 pb-3">Chat</h2>
        <p className="text-gray-500 text-sm px-6">Ask questions about your documents.</p>
      </main>
    </div>
  )
}

export default App
