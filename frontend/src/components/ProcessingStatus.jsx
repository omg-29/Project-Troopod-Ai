import React, { useMemo } from 'react';
import { STAGE_LIST } from '../utils/constants';

/**
 * Multi-stage progress indicator with vertical stepper UI.
 *
 * @param {{ events: Array, latestEvent: object|null, error: string|null }} props
 */
export default function ProcessingStatus({ events, latestEvent, error }) {
  const stageStatuses = useMemo(() => {
    const statuses = {};

    STAGE_LIST.forEach((stage) => {
      statuses[stage.id] = 'pending';
    });

    if (!latestEvent) return statuses;

    const currentStageId = latestEvent.stage;

    STAGE_LIST.forEach((stage) => {
      const stageEvents = events.filter((e) => e.stage === stage.id);

      if (stageEvents.length === 0) {
        // Check if a later stage is active or complete, meaning this one completed
        const laterStageActive = STAGE_LIST.some(
          (s) =>
            s.order > stage.order &&
            events.some((e) => e.stage === s.id)
        );
        if (laterStageActive) {
          statuses[stage.id] = 'complete';
        }
      } else if (stage.id === currentStageId && !latestEvent.completed) {
        statuses[stage.id] = error ? 'error' : 'active';
      } else {
        // This stage has events but is not the current active one
        const laterStageActive = STAGE_LIST.some(
          (s) =>
            s.order > stage.order &&
            events.some((e) => e.stage === s.id)
        );
        if (laterStageActive || latestEvent.completed) {
          statuses[stage.id] = 'complete';
        } else if (stage.id === currentStageId) {
          statuses[stage.id] = error ? 'error' : 'active';
        }
      }
    });

    // Mark error stage
    if (error && currentStageId !== 'complete' && currentStageId !== 'error') {
      statuses[currentStageId] = 'error';
    }
    if (error && latestEvent.stage === 'error') {
      // Find last non-error stage
      const stageEvents = events.filter((e) => e.stage !== 'error' && e.stage !== 'complete');
      if (stageEvents.length > 0) {
        const lastStage = stageEvents[stageEvents.length - 1].stage;
        statuses[lastStage] = 'error';
      }
    }

    return statuses;
  }, [events, latestEvent, error]);

  const progress = latestEvent?.progress || 0;

  return (
    <div className="glass-strong rounded-2xl p-8 animate-slide-up" id="processing-status">
      <h2 className="text-lg font-bold text-surface-100 mb-2">Optimizing Your Page</h2>
      <p className="text-sm text-surface-400 mb-6">
        {error ? 'An error occurred during processing.' : 'Running the CRO pipeline. This may take a minute.'}
      </p>

      {/* Progress bar */}
      <div className="progress-bar-track mb-8">
        <div className="progress-bar-fill" style={{ width: `${progress}%` }} />
      </div>

      {/* Stepper */}
      <div className="space-y-4">
        {STAGE_LIST.map((stage, index) => {
          const status = stageStatuses[stage.id] || 'pending';
          const stageMessage = [...events]
            .reverse()
            .find((e) => e.stage === stage.id)?.message;

          return (
            <div key={stage.id} className="flex items-start gap-4">
              {/* Vertical line connector */}
              <div className="flex flex-col items-center">
                <div className={`step-indicator step-${status}`}>
                  {status === 'complete' ? (
                    <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="3" strokeLinecap="round" strokeLinejoin="round">
                      <polyline points="20 6 9 17 4 12" />
                    </svg>
                  ) : status === 'error' ? (
                    <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="3" strokeLinecap="round" strokeLinejoin="round">
                      <line x1="18" y1="6" x2="6" y2="18" />
                      <line x1="6" y1="6" x2="18" y2="18" />
                    </svg>
                  ) : (
                    <span>{index + 1}</span>
                  )}
                </div>
                {index < STAGE_LIST.length - 1 && (
                  <div className={`w-px h-6 mt-1 transition-colors duration-300 ${
                    status === 'complete' ? 'bg-success/40' : 'bg-surface-700'
                  }`} />
                )}
              </div>

              {/* Content */}
              <div className="flex-1 pb-2">
                <div className="flex items-center gap-2">
                  <h3 className={`text-sm font-semibold transition-colors ${
                    status === 'active' ? 'text-accent-light' :
                    status === 'complete' ? 'text-success' :
                    status === 'error' ? 'text-danger' :
                    'text-surface-500'
                  }`}>
                    {stage.label}
                  </h3>
                  {status === 'active' && (
                    <span className="flex h-2 w-2">
                      <span className="animate-ping absolute inline-flex h-2 w-2 rounded-full bg-accent opacity-75" />
                      <span className="relative inline-flex rounded-full h-2 w-2 bg-accent-light" />
                    </span>
                  )}
                </div>
                <p className={`text-xs mt-0.5 transition-colors ${
                  status === 'active' || status === 'complete' ? 'text-surface-300' : 'text-surface-600'
                }`}>
                  {stageMessage || stage.description}
                </p>
              </div>
            </div>
          );
        })}
      </div>

      {/* Error message */}
      {error && (
        <div className="mt-6 p-4 rounded-xl bg-danger/10 border border-danger/20">
          <p className="text-sm text-danger font-medium">Error</p>
          <p className="text-xs text-danger/80 mt-1">{error}</p>
        </div>
      )}
    </div>
  );
}
