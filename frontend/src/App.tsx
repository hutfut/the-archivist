import './App.css'

function App() {
  return (
    <div className="app-layout">
      <aside className="panel documents-panel">
        <h2>Documents</h2>
        <p className="placeholder-text">Upload and manage documents here.</p>
      </aside>
      <main className="panel chat-panel">
        <h2>Chat</h2>
        <p className="placeholder-text">Ask questions about your documents.</p>
      </main>
    </div>
  )
}

export default App
