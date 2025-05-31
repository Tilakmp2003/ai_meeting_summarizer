import React, { useState } from 'react';
import './App.css';

function App() {
  const [transcriptText, setTranscriptText] = useState('');
  const [transcriptFile, setTranscriptFile] = useState(null);
  const [summary, setSummary] = useState('');
  const [decisions, setDecisions] = useState([]);
  const [actionItems, setActionItems] = useState([]);
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState('');

  const handleTextChange = (event) => {
    setTranscriptText(event.target.value);
    if (event.target.value) { // If text is entered, clear any selected file
        setTranscriptFile(null);
        const fileInput = document.getElementById('transcript_file_input');
        if (fileInput) fileInput.value = ''; // Clear the file input visually
    }
  };

  const handleFileChange = (event) => {
    setTranscriptFile(event.target.files[0]);
    if (event.target.files[0]) { // If file is selected, clear any typed text
        setTranscriptText('');
    }
  };

  const handleSubmit = async (event) => {
    event.preventDefault();
    setIsLoading(true);
    setError('');
    setSummary('');
    setDecisions([]);
    setActionItems([]);

    let requestBody;
    let headers = {};

    if (transcriptText.trim()) {
      requestBody = JSON.stringify({ transcript_text: transcriptText });
      headers['Content-Type'] = 'application/json';
    } else if (transcriptFile) {
      const formData = new FormData();
      formData.append('transcript_file', transcriptFile);
      requestBody = formData;
      // Content-Type for FormData is set automatically by the browser
    } else {
      setError('Please provide a transcript either by pasting text or uploading a file.');
      setIsLoading(false);
      return;
    }

    try {
      const response = await fetch('/api/summarize', {
        method: 'POST',
        headers: headers,
        body: requestBody,
      });

      const data = await response.json();

      if (!response.ok) {
        throw new Error(data.error || `HTTP error! status: ${response.status}`);
      }

      setSummary(data.summary || '');
      setDecisions(data.decisions || []);
      setActionItems(data.action_items || []);

    } catch (e) {
      console.error("Error submitting transcript:", e);
      setError(e.message || 'Failed to summarize transcript. Please try again.');
    } finally {
      setIsLoading(false);
    }
  };

  return (
    <div className="App">
      <header className="App-header">
        <h1>AI Meeting Summarizer</h1>
      </header>
      <main className="App-main">
        <form onSubmit={handleSubmit} className="transcript-form">
          <div className="form-group">
            <label htmlFor="transcript_text_area">Option 1: Paste transcript text</label>
            <textarea
              id="transcript_text_area"
              value={transcriptText}
              onChange={handleTextChange}
              rows="10"
              placeholder="Paste your meeting transcript here..."
            />
          </div>
          <div className="form-separator">OR</div>
          <div className="form-group">
            <label htmlFor="transcript_file_input">Option 2: Upload a .txt transcript file</label>
            <input
              type="file"
              id="transcript_file_input"
              accept=".txt"
              onChange={handleFileChange}
            />
          </div>
          <button type="submit" disabled={isLoading || (!transcriptText.trim() && !transcriptFile)}>
            {isLoading ? 'Summarizing...' : 'Summarize'}
          </button>
        </form>

        {error && <div className="error-message">{error}</div>}

        {isLoading && <div className="loading-message">Processing... please wait.</div>}

        {!isLoading && (summary || decisions.length > 0 || actionItems.length > 0) && (
          <div className="results-section">
            {summary && (
              <div className="result-category">
                <h2>Summary</h2>
                <p>{summary}</p>
              </div>
            )}
            {decisions.length > 0 && (
              <div className="result-category">
                <h2>Key Decisions</h2>
                <ul>
                  {decisions.map((decision, index) => (
                    <li key={`decision-${index}`}>{decision}</li>
                  ))}
                </ul>
              </div>
            )}
            {actionItems.length > 0 && (
              <div className="result-category">
                <h2>Action Items</h2>
                <ul>
                  {actionItems.map((item, index) => (
                    <li key={`action-${index}`}>{item}</li>
                  ))}
                </ul>
              </div>
            )}
          </div>
        )}
      </main>
    </div>
  );
}

export default App;
