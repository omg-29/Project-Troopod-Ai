import React from 'react';

/**
 * Layout shell with dark background, animated gradient orbs, and centered content.
 */
export default function Layout({ children }) {
  return (
    <div className="relative min-h-screen bg-surface-950 overflow-hidden">
      {/* Animated background orbs */}
      <div className="bg-orb bg-orb-1" aria-hidden="true" />
      <div className="bg-orb bg-orb-2" aria-hidden="true" />
      <div className="bg-orb bg-orb-3" aria-hidden="true" />

      {/* Header */}
      <header className="relative z-10 pt-8 pb-4 px-6">
        <div className="max-w-5xl mx-auto flex items-center justify-between">
          <div className="flex items-center gap-3">
            {/* Brand mark */}
            <div className="w-9 h-9 rounded-lg flex items-center justify-center"
                 style={{ background: 'var(--accent-gradient)' }}>
              <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="white" strokeWidth="2.5" strokeLinecap="round" strokeLinejoin="round">
                <path d="M12 2L2 7l10 5 10-5-10-5z" />
                <path d="M2 17l10 5 10-5" />
                <path d="M2 12l10 5 10-5" />
              </svg>
            </div>
            <h1 className="text-xl font-bold tracking-tight">
              <span className="gradient-text">Troopod</span>
            </h1>
          </div>
          <span className="text-xs text-surface-500 font-medium tracking-wide uppercase">
            AI-Powered CRO
          </span>
        </div>
      </header>

      {/* Main content */}
      <main className="relative z-10 px-6 pb-16">
        <div className="max-w-5xl mx-auto">
          {children}
        </div>
      </main>

      {/* Footer */}
      <footer className="relative z-10 py-6 px-6 border-t border-surface-800/50">
        <div className="max-w-5xl mx-auto text-center">
          <p className="text-xs text-surface-600">
            Troopod CRO Engine -- Conversion Rate Optimization powered by AI
          </p>
        </div>
      </footer>
    </div>
  );
}
