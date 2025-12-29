import React, { useState, useRef } from 'react';
import { useNavigate } from 'react-router-dom';
import { documentAPI } from '../services/api';
import './UploadDocument.css';

const UploadDocument = () => {
  const [files, setFiles] = useState([]);
  const [formData, setFormData] = useState({
    document_type: 'consent_form',
    patient_name: '',
    patient_id: '',
  });
  const [uploading, setUploading] = useState(false);
  const [uploadProgress, setUploadProgress] = useState({ current: 0, total: 0 });
  const [error, setError] = useState('');
  const [dragActive, setDragActive] = useState(false);
  const fileInputRef = useRef(null);
  const navigate = useNavigate();

  const validateFile = (file) => {
    if (file.type !== 'application/pdf') {
      return 'Only PDF files are allowed';
    }
    if (file.size > 16 * 1024 * 1024) {
      return 'File size must be less than 16MB';
    }
    return null;
  };

  const handleFiles = (selectedFiles) => {
    if (!selectedFiles || selectedFiles.length === 0) return;

    const fileArray = Array.from(selectedFiles);
    const validFiles = [];
    const errors = [];

    fileArray.forEach(file => {
      const error = validateFile(file);
      if (error) {
        errors.push(`${file.name}: ${error}`);
      } else {
        // Check for duplicates
        if (!files.some(f => f.name === file.name && f.size === file.size)) {
          validFiles.push(file);
        }
      }
    });

    if (errors.length > 0) {
      setError(errors.join('\n'));
    } else {
      setError('');
    }

    if (validFiles.length > 0) {
      setFiles(prev => [...prev, ...validFiles]);
    }
  };

  const handleDrop = (e) => {
    e.preventDefault();
    setDragActive(false);
    handleFiles(e.dataTransfer.files);
  };

  const handleChange = (e) => {
    setFormData({
      ...formData,
      [e.target.name]: e.target.value,
    });
  };

  const removeFile = (index) => {
    setFiles(prev => prev.filter((_, i) => i !== index));
  };

  const handleSubmit = async (e) => {
    e.preventDefault();

    if (files.length === 0) {
      setError('Please select at least one PDF file');
      return;
    }

    setUploading(true);
    setError('');
    setUploadProgress({ current: 0, total: files.length });

    const results = { success: 0, failed: [] };

    for (let i = 0; i < files.length; i++) {
      const file = files[i];
      setUploadProgress({ current: i + 1, total: files.length });

      try {
        const data = new FormData();
        data.append('file', file);
        data.append('document_type', formData.document_type);
        data.append('patient_name', formData.patient_name);
        data.append('patient_id', formData.patient_id);

        await documentAPI.upload(data);
        results.success++;
      } catch (err) {
        results.failed.push({
          name: file.name,
          error: err.response?.data?.error || 'Upload failed'
        });
      }
    }

    setUploading(false);

    if (results.failed.length === 0) {
      alert(`Successfully uploaded ${results.success} document${results.success !== 1 ? 's' : ''}!`);
      navigate('/documents');
    } else if (results.success > 0) {
      alert(`Uploaded ${results.success} document${results.success !== 1 ? 's' : ''}. ${results.failed.length} failed.`);
      setFiles([]); // Clear successfully uploaded files
      setError(results.failed.map(f => `${f.name}: ${f.error}`).join('\n'));
    } else {
      setError(results.failed.map(f => `${f.name}: ${f.error}`).join('\n'));
    }
  };

  const totalSize = files.reduce((sum, f) => sum + f.size, 0);

  return (
    <div className="upload-page">
      <div className="upload-container">
        <h1>Upload Documents</h1>
        <p className="upload-subtitle">Upload PDF documents for doctors to sign</p>

        <form onSubmit={handleSubmit}>
          <div
            className={`drop-zone ${dragActive ? 'active' : ''} ${files.length > 0 ? 'has-file' : ''}`}
            onDrop={handleDrop}
            onDragOver={(e) => { e.preventDefault(); setDragActive(true); }}
            onDragLeave={() => setDragActive(false)}
            onClick={() => fileInputRef.current?.click()}
          >
            {files.length > 0 ? (
              <div className="files-preview">
                <div className="files-summary" onClick={(e) => e.stopPropagation()}>
                  <span className="files-count">{files.length} file{files.length !== 1 ? 's' : ''} selected</span>
                  <span className="files-size">{(totalSize / 1024 / 1024).toFixed(2)} MB total</span>
                </div>
                <div className="files-list" onClick={(e) => e.stopPropagation()}>
                  {files.map((file, index) => (
                    <div key={`${file.name}-${index}`} className="file-item">
                      <span className="file-icon">📄</span>
                      <span className="file-name">{file.name}</span>
                      <span className="file-size">{(file.size / 1024 / 1024).toFixed(2)} MB</span>
                      <button
                        type="button"
                        className="btn-remove-file"
                        onClick={() => removeFile(index)}
                      >
                        ×
                      </button>
                    </div>
                  ))}
                </div>
                <p className="add-more-hint">Click or drag to add more files</p>
              </div>
            ) : (
              <div className="drop-content">
                <div className="drop-icon">📁</div>
                <p>Drag and drop your PDFs here</p>
                <p className="drop-hint">or click to browse (multiple files supported)</p>
              </div>
            )}

            <input
              ref={fileInputRef}
              type="file"
              accept=".pdf"
              multiple
              onChange={(e) => handleFiles(e.target.files)}
              hidden
            />
          </div>

          <div className="form-section">
            <h3>Document Details</h3>
            <p className="form-hint">These details will apply to all uploaded documents</p>

            <div className="form-group">
              <label htmlFor="document_type">Document Type</label>
              <select
                id="document_type"
                name="document_type"
                value={formData.document_type}
                onChange={handleChange}
              >
                <option value="consent_form">Consent Form</option>
                <option value="prescription">Prescription</option>
                <option value="medical_report">Medical Report</option>
                <option value="discharge_summary">Discharge Summary</option>
                <option value="referral">Referral Letter</option>
                <option value="other">Other</option>
              </select>
            </div>

            <div className="form-row">
              <div className="form-group">
                <label htmlFor="patient_name">Patient Name (Optional)</label>
                <input
                  type="text"
                  id="patient_name"
                  name="patient_name"
                  value={formData.patient_name}
                  onChange={handleChange}
                  placeholder="John Doe"
                />
              </div>

              <div className="form-group">
                <label htmlFor="patient_id">Patient ID (Optional)</label>
                <input
                  type="text"
                  id="patient_id"
                  name="patient_id"
                  value={formData.patient_id}
                  onChange={handleChange}
                  placeholder="PAT-12345"
                />
              </div>
            </div>
          </div>

          {error && <div className="form-error">{error}</div>}

          {uploading && (
            <div className="upload-progress">
              <div className="progress-text">
                Uploading {uploadProgress.current} of {uploadProgress.total}...
              </div>
              <div className="progress-bar">
                <div
                  className="progress-fill"
                  style={{ width: `${(uploadProgress.current / uploadProgress.total) * 100}%` }}
                ></div>
              </div>
            </div>
          )}

          <div className="form-actions">
            <button
              type="button"
              className="btn-cancel"
              onClick={() => navigate('/documents')}
              disabled={uploading}
            >
              Cancel
            </button>
            <button
              type="submit"
              className="btn-upload"
              disabled={files.length === 0 || uploading}
            >
              {uploading ? 'Uploading...' : `Upload ${files.length || ''} Document${files.length !== 1 ? 's' : ''}`}
            </button>
          </div>
        </form>
      </div>
    </div>
  );
};

export default UploadDocument;
