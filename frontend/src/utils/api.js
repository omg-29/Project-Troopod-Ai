import { API_URL } from './constants';

/**
 * Start the CRO generation pipeline via streaming fetch.
 * Returns a ReadableStream response for SSE parsing.
 *
 * @param {File} imageFile - Ad campaign creative (JPEG/PNG)
 * @param {string} url - Target webpage URL
 * @param {string} text - Plain text requirements
 * @returns {Promise<Response>} Fetch response with SSE stream
 */
export async function generateCRO(imageFile, url, text) {
  const formData = new FormData();
  formData.append('image', imageFile);
  formData.append('url', url);
  formData.append('text', text);

  const response = await fetch(`${API_URL}/api/generate`, {
    method: 'POST',
    body: formData,
  });

  if (!response.ok) {
    const errorData = await response.json().catch(() => ({ detail: 'Unknown error' }));
    throw new Error(errorData.detail || `Server error: ${response.status}`);
  }

  return response;
}

/**
 * Health check for the backend API.
 * @returns {Promise<boolean>}
 */
export async function checkHealth() {
  try {
    const response = await fetch(`${API_URL}/api/health`);
    return response.ok;
  } catch {
    return false;
  }
}
