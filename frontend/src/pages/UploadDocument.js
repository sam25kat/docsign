import React, { useState, useRef } from 'react';
import { useNavigate } from 'react-router-dom';
import { documentAPI } from '../services/api';
import './UploadDocument.css';

const UploadDocument = () => {
  const [file, setFile] = useState(null);
  const [preview, setPreview] = useState(null);
  const [formData, setFormData] = useState({
    document_type: 'consent_form',
    patient_name: '',
    patient_id: '',
  });
  const [uploading, setUploading] = useState(false);
  const [error, setError] = useState('');
  const [dragActive, setDragActive] = useState(false);
  const fileInputRef = useRef(null);
  const navigate = useNavigate();

  const handleFile = (selectedFile) => {
    if (!selectedFile) return;

    if (selectedFile.type !== 'application/pdf') {
      setError('Only PDF files are allowed');
      return;
    }

    if (selectedFile.size > 16 * 1024 * 1024) {
      setError('File size must be less than 16MB');
      return;
    }

    setFile(selectedFile);
    setPreview(selectedFile.name);
    setError('');
  };

  const handleDrop = (e) => {
    e.preventDefault();
    setDragActive(false);
    handleFile(e.dataTransfer.files[0]);
  };

  const handleChange = (e) => {
    setFormData({
      ...formData,
      [e.target.name]: e.target.value,
    });
  };

  const handleSubmit = async (e) => {
    e.preventDefault();

    if (!file) {
      setError('Please select a PDF file');
      return;
    }

    setUploading(true);
    setError('');

    try {
      const data = new FormData();
      data.append('file', file);
      data.append('document_type', formData.document_type);
      data.append('patient_name', formData.patient_name);
      data.append('patient_id', formData.patient_id);

      await documentAPI.upload(data);
      alert('Document uploaded successfully!');
      navigate('/documents');
    } catch (err) {
      setError(err.response?.data?.error || 'Failed to upload document');
    } finally {
      setUploading(false);
    }
  };

  return (
    <div className="upload-page">
      <div className="upload-container">
        <h1>Upload Document</h1>
        <p className="upload-subtitle">Upload a PDF document for doctors to sign</p>

        <form onSubmit={handleSubmit}>
          <div
            className={`drop-zone ${dragActive ? 'active' : ''} ${file ? 'has-file' : ''}`}
            onDrop={handleDrop}
            onDragOver={(e) => { e.preventDefault(); setDragActive(true); }}
            onDragLeave={() => setDragActive(false)}
            onClick={() => fileInputRef.current?.click()}
          >
            {file ? (
              <div className="file-preview">
                <div className="file-icon">📄</div>
                <p className="file-name">{preview}</p>
                <p className="file-size">{(file.size / 1024 / 1024).toFixed(2)} MB</p>
                <button
                  type="button"
                  className="btn-remove"
                  onClick={(e) => {
                    e.stopPropagation();
                    setFile(null);
                    setPreview(null);
                  }}
                >
                  Remove
                </button>
              </div>
            ) : (
              <div className="drop-content">
                <div className="drop-icon">📁</div>
                <p>Drag and drop your PDF here</p>
                <p className="drop-hint">or click to browse</p>
              </div>
            )}

            <input
              ref={fileInputRef}
              type="file"
              accept=".pdf"
              onChange={(e) => handleFile(e.target.files[0])}
              hidden
            />
          </div>

          <div className="form-section">
            <h3>Document Details</h3>

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

          <div className="form-actions">
            <button
              type="button"
              className="btn-cancel"
              onClick={() => navigate('/documents')}
            >
              Cancel
            </button>
            <button
              type="submit"
              className="btn-upload"
              disabled={!file || uploading}
            >
              {uploading ? 'Uploading...' : 'Upload Document'}
            </button>
          </div>
        </form>
      </div>
    </div>
  );
};

export default UploadDocument;
