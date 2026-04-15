import React, { useState } from 'react';

const STEPS = [
  {
    number: '01',
    title: 'Upload Ad Creative',
    description: 'Upload your campaign image (JPEG or PNG, max 5MB). The AI will extract visual context, text overlays, and offers.',
  },
  {
    number: '02',
    title: 'Paste Target URL',
    description: 'Provide the landing page URL you want to optimize. The system will scrape and analyze its structure.',
  },
  {
    number: '03',
    title: 'Describe Requirements',
    description: 'Detail your CRO goals: product info, desired CTA text, target audience, and any specific banner or segment requirements.',
  },
];

/**
 * Collapsible "How to Use" guide with 3-step instructions.
 */
export default function HowToUse() {
  const [isExpanded, setIsExpanded] = useState(false);

  return (
    <div className="glass rounded-xl mb-8 overflow-hidden animate-fade-in">
      <button
        id="how-to-use-toggle"
        onClick={() => setIsExpanded(!isExpanded)}
        className="w-full flex items-center justify-between px-6 py-4 text-left hover:bg-white/[0.02] transition-colors"
        aria-expanded={isExpanded}
        aria-controls="how-to-use-content"
      >
        <div className="flex items-center gap-3">
          <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" className="text-accent-light">
            <circle cx="12" cy="12" r="10" />
            <path d="M9.09 9a3 3 0 0 1 5.83 1c0 2-3 3-3 3" />
            <line x1="12" y1="17" x2="12.01" y2="17" />
          </svg>
          <span className="text-sm font-semibold text-surface-200">How to Use Troopod</span>
        </div>
        <svg
          width="16"
          height="16"
          viewBox="0 0 24 24"
          fill="none"
          stroke="currentColor"
          strokeWidth="2"
          strokeLinecap="round"
          strokeLinejoin="round"
          className={`text-surface-400 transition-transform duration-300 ${isExpanded ? 'rotate-180' : ''}`}
        >
          <polyline points="6 9 12 15 18 9" />
        </svg>
      </button>

      <div
        id="how-to-use-content"
        className={`transition-all duration-400 ease-in-out overflow-hidden ${
          isExpanded ? 'max-h-96 opacity-100' : 'max-h-0 opacity-0'
        }`}
      >
        <div className="px-6 pb-6 pt-2">
          <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
            {STEPS.map((step, index) => (
              <div
                key={step.number}
                className={`glass-subtle rounded-lg p-4 stagger-${index + 1} ${isExpanded ? 'animate-slide-up' : ''}`}
              >
                <div className="text-xs font-bold text-accent-light mb-2 tracking-wider">
                  STEP {step.number}
                </div>
                <h3 className="text-sm font-semibold text-surface-100 mb-1.5">
                  {step.title}
                </h3>
                <p className="text-xs text-surface-400 leading-relaxed">
                  {step.description}
                </p>
              </div>
            ))}
          </div>
        </div>
      </div>
    </div>
  );
}
