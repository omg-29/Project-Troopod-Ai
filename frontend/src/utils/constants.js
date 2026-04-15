export const STAGES = {
  extraction: {
    id: 'extraction',
    label: 'Extraction',
    description: 'Analyzing text requirements',
    order: 1,
  },
  analysis: {
    id: 'analysis',
    label: 'Analysis',
    description: 'Processing ad creative with AI vision',
    order: 2,
  },
  scraping: {
    id: 'scraping',
    label: 'Scraping',
    description: 'Capturing target webpage',
    order: 3,
  },
  generation: {
    id: 'generation',
    label: 'Generation',
    description: 'Injecting CRO optimizations',
    order: 4,
  },
};

export const STAGE_LIST = Object.values(STAGES).sort((a, b) => a.order - b.order);

export const MAX_FILE_SIZE_MB = 5;
export const MAX_FILE_SIZE_BYTES = MAX_FILE_SIZE_MB * 1024 * 1024;
export const ALLOWED_MIME_TYPES = ['image/jpeg', 'image/png'];
export const ALLOWED_EXTENSIONS = '.jpg,.jpeg,.png';

export const API_URL = import.meta.env.VITE_API_URL || 'http://localhost:8000';
