import React, { useState, useCallback } from 'react';
import Layout from './components/Layout';
import HowToUse from './components/HowToUse';
import InputForm from './components/InputForm';
import ProcessingStatus from './components/ProcessingStatus';
import PreviewFrame from './components/PreviewFrame';
import { useSSE } from './hooks/useSSE';

/**
 * Root application component.
 * Manages global state and renders the appropriate view:
 *   1. Input Form (default)
 *   2. Processing Status (while pipeline is running)
 *   3. Preview Frame (when result is ready)
 */
export default function App() {
  const {
    startGeneration,
    events,
    latestEvent,
    result,
    error,
    isProcessing,
    reset,
  } = useSSE();

  const [view, setView] = useState('form'); // 'form' | 'processing' | 'preview'

  const handleSubmit = useCallback(
    async (imageFile, url, text) => {
      setView('processing');
      await startGeneration(imageFile, url, text);
    },
    [startGeneration]
  );

  const handleReset = useCallback(() => {
    reset();
    setView('form');
  }, [reset]);

  // Automatically transition to preview when result arrives
  React.useEffect(() => {
    if (result && !error) {
      setView('preview');
    }
  }, [result, error]);

  // Transition back to processing if error occurs during processing
  React.useEffect(() => {
    if (error && view === 'processing') {
      // Stay on processing view to show the error in stepper
    }
  }, [error, view]);

  return (
    <Layout>
      {/* Hero text - only on form view */}
      {view === 'form' && (
        <div className="text-center mb-10 pt-6 animate-fade-in">
          <h2 className="text-3xl md:text-4xl font-extrabold tracking-tight mb-3">
            <span className="gradient-text">Optimize Conversions</span>
            <br />
            <span className="text-surface-200">with AI Precision</span>
          </h2>
          <p className="text-sm text-surface-400 max-w-lg mx-auto leading-relaxed">
            Dynamically personalize any landing page to match your ad campaign.
            Upload your creative, paste the URL, and let Troopod handle the rest.
          </p>
        </div>
      )}

      {/* How to Use guide - only on form view */}
      {view === 'form' && <HowToUse />}

      {/* Main content */}
      {view === 'form' && (
        <InputForm onSubmit={handleSubmit} isProcessing={isProcessing} />
      )}

      {view === 'processing' && (
        <div className="max-w-2xl mx-auto mt-8">
          <ProcessingStatus
            events={events}
            latestEvent={latestEvent}
            error={error}
          />
          {error && (
            <div className="mt-6 text-center">
              <button
                onClick={handleReset}
                id="retry-btn"
                className="btn-primary text-sm px-6 py-2.5"
              >
                Try Again
              </button>
            </div>
          )}
        </div>
      )}

      {view === 'preview' && (
        <div className="mt-4">
          <PreviewFrame result={result} onReset={handleReset} />
        </div>
      )}
    </Layout>
  );
}
