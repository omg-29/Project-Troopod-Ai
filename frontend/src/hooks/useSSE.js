import { useState, useCallback, useRef } from 'react';
import { generateCRO } from '../utils/api';

/**
 * Custom hook for Server-Sent Events streaming from the CRO pipeline.
 *
 * Uses fetch() with ReadableStream since our endpoint is POST (EventSource only supports GET).
 *
 * @returns {{ startGeneration, events, latestEvent, result, error, isProcessing, reset }}
 */
export function useSSE() {
  const [events, setEvents] = useState([]);
  const [latestEvent, setLatestEvent] = useState(null);
  const [result, setResult] = useState(null);
  const [error, setError] = useState(null);
  const [isProcessing, setIsProcessing] = useState(false);
  const abortRef = useRef(null);

  const reset = useCallback(() => {
    setEvents([]);
    setLatestEvent(null);
    setResult(null);
    setError(null);
    setIsProcessing(false);
    if (abortRef.current) {
      abortRef.current.abort();
      abortRef.current = null;
    }
  }, []);

  const startGeneration = useCallback(async (imageFile, url, text) => {
    reset();
    setIsProcessing(true);

    try {
      const response = await generateCRO(imageFile, url, text);
      const reader = response.body.getReader();
      const decoder = new TextDecoder();
      let buffer = '';

      while (true) {
        const { done, value } = await reader.read();

        if (done) break;

        buffer += decoder.decode(value, { stream: true });

        // Parse SSE events from buffer
        const lines = buffer.split('\n');
        buffer = lines.pop() || '';

        for (const line of lines) {
          const trimmed = line.trim();
          if (!trimmed.startsWith('data: ')) continue;

          const jsonStr = trimmed.substring(6);
          if (!jsonStr) continue;

          try {
            const eventData = JSON.parse(jsonStr);

            setEvents((prev) => [...prev, eventData]);
            setLatestEvent(eventData);

            // Check for completion
            if (eventData.completed && eventData.result) {
              setResult(eventData.result);
              setIsProcessing(false);
            }

            // Check for error
            if (eventData.stage === 'error' || eventData.error) {
              setError(eventData.message || eventData.error?.detail || 'Pipeline error');
              setIsProcessing(false);
            }
          } catch (parseErr) {
            console.warn('Failed to parse SSE event:', parseErr);
          }
        }
      }
    } catch (fetchErr) {
      setError(fetchErr.message || 'Connection to server failed');
      setIsProcessing(false);
    }
  }, [reset]);

  return {
    startGeneration,
    events,
    latestEvent,
    result,
    error,
    isProcessing,
    reset,
  };
}
