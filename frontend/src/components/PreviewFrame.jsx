import React, { useState, useMemo } from 'react';

const VIEWPORTS = {
  desktop: { width: '100%', label: 'Desktop' },
  tablet: { width: '768px', label: 'Tablet' },
  mobile: { width: '375px', label: 'Mobile' },
};

/**
 * Secure iframe preview renderer with device viewport toggle.
 *
 * @param {{ result: { modified_html: string, modified_css: string, modified_js: string }, onReset: () => void }} props
 */
export default function PreviewFrame({ result, onReset }) {
  const [viewport, setViewport] = useState('desktop');

  const srcDoc = useMemo(() => {
    if (!result?.modified_html) return '';
    return result.modified_html;
  }, [result]);

  return (
    <div className="animate-slide-up" id="preview-section">
      {/* Toolbar */}
      <div className="glass-strong rounded-t-2xl px-6 py-4 flex items-center justify-between border-b border-surface-700/50">
        <div>
          <h2 className="text-lg font-bold text-surface-100">CRO Preview</h2>
          <p className="text-xs text-surface-500 mt-0.5">Your optimized landing page preview</p>
        </div>

        <div className="flex items-center gap-3">
          {/* Viewport toggle */}
          <div className="glass-subtle rounded-lg p-1 flex gap-1">
            {Object.entries(VIEWPORTS).map(([key, val]) => (
              <button
                key={key}
                id={`viewport-${key}`}
                onClick={() => setViewport(key)}
                className={`px-3 py-1.5 rounded-md text-xs font-medium transition-all ${
                  viewport === key
                    ? 'bg-accent/20 text-accent-light'
                    : 'text-surface-400 hover:text-surface-200'
                }`}
              >
                {val.label}
              </button>
            ))}
          </div>

          {/* Back button */}
          <button
            onClick={onReset}
            id="back-to-form-btn"
            className="flex items-center gap-2 px-4 py-2 rounded-lg text-xs font-medium text-surface-300 hover:text-surface-100 glass-subtle hover:bg-white/5 transition-colors"
          >
            <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
              <line x1="19" y1="12" x2="5" y2="12" />
              <polyline points="12 19 5 12 12 5" />
            </svg>
            New Optimization
          </button>
        </div>
      </div>

      {/* Iframe container */}
      <div className="bg-surface-900 rounded-b-2xl overflow-hidden flex justify-center p-4">
        <div
          className="bg-white rounded-lg overflow-hidden transition-all duration-300 shadow-2xl"
          style={{
            width: VIEWPORTS[viewport].width,
            maxWidth: '100%',
          }}
        >
          <iframe
            id="preview-iframe"
            title="CRO Preview"
            srcDoc={srcDoc}
            sandbox="allow-scripts allow-same-origin"
            className="w-full border-0"
            style={{ height: '80vh', minHeight: '600px' }}
            referrerPolicy="no-referrer"
          />
        </div>
      </div>
    </div>
  );
}
