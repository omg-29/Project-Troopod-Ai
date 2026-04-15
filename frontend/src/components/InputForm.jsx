import React, { useState, useRef, useCallback } from 'react';
import {
  MAX_FILE_SIZE_BYTES,
  MAX_FILE_SIZE_MB,
  ALLOWED_MIME_TYPES,
  ALLOWED_EXTENSIONS,
} from '../utils/constants';

/**
 * Input form with image upload (drag-and-drop), URL field, text area, and generate button.
 *
 * @param {{ onSubmit: (file, url, text) => void, isProcessing: boolean }} props
 */
export default function InputForm({ onSubmit, isProcessing }) {
  const [imageFile, setImageFile] = useState(null);
  const [imagePreview, setImagePreview] = useState(null);
  const [url, setUrl] = useState('');
  const [text, setText] = useState('');
  const [dragOver, setDragOver] = useState(false);
  const [errors, setErrors] = useState({});
  const fileInputRef = useRef(null);

  const validateImage = useCallback((file) => {
    if (!file) return 'Please upload an image file.';
    if (!ALLOWED_MIME_TYPES.includes(file.type)) {
      return `Invalid format. Accepted: JPEG, PNG only.`;
    }
    if (file.size > MAX_FILE_SIZE_BYTES) {
      return `File exceeds ${MAX_FILE_SIZE_MB}MB limit (${(file.size / 1024 / 1024).toFixed(1)}MB).`;
    }
    return null;
  }, []);

  const handleImageSelect = useCallback((file) => {
    const error = validateImage(file);
    if (error) {
      setErrors((prev) => ({ ...prev, image: error }));
      setImageFile(null);
      setImagePreview(null);
      return;
    }
    setErrors((prev) => ({ ...prev, image: null }));
    setImageFile(file);

    const reader = new FileReader();
    reader.onload = (e) => setImagePreview(e.target.result);
    reader.readAsDataURL(file);
  }, [validateImage]);

  const handleDrop = useCallback((e) => {
    e.preventDefault();
    setDragOver(false);
    const file = e.dataTransfer.files?.[0];
    if (file) handleImageSelect(file);
  }, [handleImageSelect]);

  const handleDragOver = useCallback((e) => {
    e.preventDefault();
    setDragOver(true);
  }, []);

  const handleDragLeave = useCallback((e) => {
    e.preventDefault();
    setDragOver(false);
  }, []);

  const removeImage = useCallback(() => {
    setImageFile(null);
    setImagePreview(null);
    setErrors((prev) => ({ ...prev, image: null }));
    if (fileInputRef.current) fileInputRef.current.value = '';
  }, []);

  const validateUrl = useCallback((value) => {
    if (!value.trim()) return 'URL is required.';
    try {
      const parsed = new URL(value);
      if (!['http:', 'https:'].includes(parsed.protocol)) {
        return 'URL must start with http:// or https://';
      }
    } catch {
      return 'Please enter a valid URL.';
    }
    return null;
  }, []);

  const handleSubmit = useCallback((e) => {
    e.preventDefault();

    const imageError = validateImage(imageFile);
    const urlError = validateUrl(url);
    const textError = !text.trim() ? 'Requirements text is required.' : null;

    setErrors({ image: imageError, url: urlError, text: textError });

    if (imageError || urlError || textError) return;

    onSubmit(imageFile, url.trim(), text.trim());
  }, [imageFile, url, text, onSubmit, validateImage, validateUrl]);

  const isValid = imageFile && url.trim() && text.trim() && !errors.image;

  return (
    <form onSubmit={handleSubmit} className="glass-strong rounded-2xl p-8 animate-slide-up" id="input-form">
      <h2 className="text-lg font-bold text-surface-100 mb-1">Configure Optimization</h2>
      <p className="text-sm text-surface-400 mb-8">Provide your ad creative, target page, and CRO requirements.</p>

      {/* Image Upload */}
      <div className="mb-6">
        <label htmlFor="image-upload" className="block text-sm font-medium text-surface-300 mb-2">
          Ad Campaign Creative
        </label>

        {!imagePreview ? (
          <div
            className={`drop-zone ${dragOver ? 'drag-over' : ''}`}
            onDrop={handleDrop}
            onDragOver={handleDragOver}
            onDragLeave={handleDragLeave}
            onClick={() => fileInputRef.current?.click()}
            role="button"
            tabIndex={0}
            id="image-drop-zone"
          >
            <svg width="32" height="32" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round" className="mx-auto mb-3 text-surface-500">
              <rect x="3" y="3" width="18" height="18" rx="2" ry="2" />
              <circle cx="8.5" cy="8.5" r="1.5" />
              <polyline points="21 15 16 10 5 21" />
            </svg>
            <p className="text-sm text-surface-300 mb-1">Drop your image here or click to browse</p>
            <p className="text-xs text-surface-500">JPEG or PNG, max {MAX_FILE_SIZE_MB}MB</p>
          </div>
        ) : (
          <div className="relative glass-subtle rounded-xl p-3 flex items-center gap-4">
            <img
              src={imagePreview}
              alt="Ad creative preview"
              className="w-20 h-20 object-cover rounded-lg border border-surface-700"
            />
            <div className="flex-1 min-w-0">
              <p className="text-sm font-medium text-surface-200 truncate">{imageFile?.name}</p>
              <p className="text-xs text-surface-500">{(imageFile?.size / 1024).toFixed(0)} KB</p>
            </div>
            <button
              type="button"
              onClick={removeImage}
              className="flex-shrink-0 w-8 h-8 rounded-lg flex items-center justify-center text-surface-400 hover:text-danger hover:bg-danger/10 transition-colors"
              aria-label="Remove image"
              id="remove-image-btn"
            >
              <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
                <line x1="18" y1="6" x2="6" y2="18" />
                <line x1="6" y1="6" x2="18" y2="18" />
              </svg>
            </button>
          </div>
        )}

        <input
          ref={fileInputRef}
          type="file"
          id="image-upload"
          accept={ALLOWED_EXTENSIONS}
          onChange={(e) => {
            const file = e.target.files?.[0];
            if (file) handleImageSelect(file);
          }}
          className="hidden"
        />

        {errors.image && (
          <p className="mt-2 text-xs text-danger">{errors.image}</p>
        )}
      </div>

      {/* URL Input */}
      <div className="mb-6">
        <label htmlFor="target-url" className="block text-sm font-medium text-surface-300 mb-2">
          Target Webpage URL
        </label>
        <input
          type="url"
          id="target-url"
          className="input-field"
          placeholder="https://example.com/landing-page"
          value={url}
          onChange={(e) => {
            setUrl(e.target.value);
            if (errors.url) setErrors((prev) => ({ ...prev, url: null }));
          }}
          onBlur={() => {
            if (url.trim()) {
              const err = validateUrl(url);
              if (err) setErrors((prev) => ({ ...prev, url: err }));
            }
          }}
        />
        {errors.url && (
          <p className="mt-2 text-xs text-danger">{errors.url}</p>
        )}
      </div>

      {/* Text Requirements */}
      <div className="mb-8">
        <label htmlFor="text-requirements" className="block text-sm font-medium text-surface-300 mb-2">
          CRO Requirements
        </label>
        <textarea
          id="text-requirements"
          className="input-field min-h-[120px] resize-y"
          placeholder="Describe the product being promoted, desired CTA text, target audience, tone, and any specific banner or segment requirements. Example: 'We are promoting our CloudFit running shoes with a Buy 1 Get 1 50% off deal. Target audience is fitness enthusiasts aged 25-40. We want the hero section to highlight the deal with an urgent CTA.'"
          value={text}
          onChange={(e) => {
            setText(e.target.value);
            if (errors.text) setErrors((prev) => ({ ...prev, text: null }));
          }}
          rows={5}
        />
        {errors.text && (
          <p className="mt-2 text-xs text-danger">{errors.text}</p>
        )}
      </div>

      {/* Submit Button */}
      <button
        type="submit"
        id="generate-btn"
        className="btn-primary w-full text-sm flex items-center justify-center gap-2"
        disabled={!isValid || isProcessing}
      >
        {isProcessing ? (
          <>
            <svg className="animate-spin-slow w-4 h-4" viewBox="0 0 24 24" fill="none">
              <circle cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="3" strokeDasharray="31.416" strokeDashoffset="10" strokeLinecap="round" />
            </svg>
            Processing...
          </>
        ) : (
          <>
            <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
              <polygon points="13 2 3 14 12 14 11 22 21 10 12 10 13 2" />
            </svg>
            Generate CRO Optimization
          </>
        )}
      </button>
    </form>
  );
}
