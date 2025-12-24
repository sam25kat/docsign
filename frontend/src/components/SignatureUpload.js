import React, { useState, useRef } from 'react';
import { signatureAPI } from '../services/api';
import './SignatureUpload.css';

const SignatureUpload = ({ onUploadSuccess, currentSignature }) => {
  const [preview, setPreview] = useState(null);
  const [uploading, setUploading] = useState(false);
  const [error, setError] = useState('');
  const [dragActive, setDragActive] = useState(false);
  const fileInputRef = useRef(null);

  const handleFile = (file) => {
    if (!file) return;

    // Validate file type
    const validTypes = ['image/png', 'image/jpeg', 'image/webp'];
    if (!validTypes.includes(file.type)) {
      setError('Please upload a PNG, JPEG, or WEBP image');
      return;
    }

    // Validate file size (max 5MB)
    if (file.size > 5 * 1024 * 1024) {
      setError('File size must be less than 5MB');
      return;
    }

    setError('');

    // Show preview
    const reader = new FileReader();
    reader.onload = (e) => {
      setPreview(e.target.result);
    };
    reader.readAsDataURL(file);
  };

  const handleDrop = (e) => {
    e.preventDefault();
    setDragActive(false);
    const file = e.dataTransfer.files[0];
    handleFile(file);
  };

  const handleDragOver = (e) => {
    e.preventDefault();
    setDragActive(true);
  };

  const handleDragLeave = () => {
    setDragActive(false);
  };

  const handleInputChange = (e) => {
    const file = e.target.files[0];
    handleFile(file);
  };

  const handleUpload = async () => {
    if (!preview) {
      setError('Please select an image first');
      return;
    }

    setUploading(true);
    setError('');

    try {
      // Convert preview to file
      const response = await fetch(preview);
      const blob = await response.blob();

      const formData = new FormData();
      formData.append('signature', blob, 'signature.png');

      await signatureAPI.upload(formData);
      onUploadSuccess?.();
      setPreview(null);
    } catch (err) {
      setError(err.response?.data?.error || 'Failed to upload signature');
    } finally {
      setUploading(false);
    }
  };

  const handleClear = () => {
    setPreview(null);
    setError('');
    if (fileInputRef.current) {
      fileInputRef.current.value = '';
    }
  };

  return (
    <div className="signature-upload">
      <h3>Upload Your Signature</h3>
      <p className="upload-info">
        Upload an image of your signature. The background will be automatically removed.
      </p>

      {currentSignature && (
        <div className="current-signature">
          <h4>Current Signature:</h4>
          <img src={currentSignature} alt="Current signature" />
        </div>
      )}

      <div
        className={`drop-zone ${dragActive ? 'active' : ''} ${preview ? 'has-preview' : ''}`}
        onDrop={handleDrop}
        onDragOver={handleDragOver}
        onDragLeave={handleDragLeave}
        onClick={() => fileInputRef.current?.click()}
      >
        {preview ? (
          <div className="preview-container">
            <img src={preview} alt="Signature preview" />
            <p>Click to change or drop a new image</p>
          </div>
        ) : (
          <div className="drop-content">
            <div className="drop-icon">📝</div>
            <p>Drag and drop your signature image here</p>
            <p className="drop-hint">or click to browse</p>
            <p className="supported-formats">Supported: PNG, JPEG, WEBP (max 5MB)</p>
          </div>
        )}

        <input
          ref={fileInputRef}
          type="file"
          accept="image/png,image/jpeg,image/webp"
          onChange={handleInputChange}
          hidden
        />
      </div>

      {error && <div className="upload-error">{error}</div>}

      <div className="upload-actions">
        {preview && (
          <>
            <button className="btn-clear" onClick={handleClear} disabled={uploading}>
              Clear
            </button>
            <button className="btn-upload" onClick={handleUpload} disabled={uploading}>
              {uploading ? 'Processing...' : 'Upload & Process'}
            </button>
          </>
        )}
      </div>

      <div className="upload-tips">
        <h4>Tips for best results:</h4>
        <ul>
          <li>Sign on white paper with a dark pen</li>
          <li>Take a photo in good lighting</li>
          <li>Crop the image to just the signature</li>
          <li>Higher resolution = better quality</li>
        </ul>
      </div>
    </div>
  );
};

export default SignatureUpload;
