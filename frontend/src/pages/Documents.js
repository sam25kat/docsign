import React, { useState, useEffect, useCallback } from 'react';
import { Link, useNavigate } from 'react-router-dom';
import { documentAPI } from '../services/api';
import { useAuth } from '../context/AuthContext';
import BulkSignModal from '../components/BulkSignModal';
import './Documents.css';

const Documents = () => {
  const [documents, setDocuments] = useState([]);
  const [filter, setFilter] = useState('pending');
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');
  const { isAdmin, hasSignature } = useAuth();
  const navigate = useNavigate();

  // Bulk selection state
  const [selectedDocs, setSelectedDocs] = useState([]);
  const [showBulkModal, setShowBulkModal] = useState(false);
  const [autoMode, setAutoMode] = useState(false);

  const fetchDocuments = useCallback(async () => {
    setLoading(true);
    try {
      const response = await documentAPI.list(filter);
      setDocuments(response.data);
      setError('');
      setSelectedDocs([]); // Clear selection on refresh
    } catch (err) {
      setError('Failed to load documents');
      console.error(err);
    } finally {
      setLoading(false);
    }
  }, [filter]);

  useEffect(() => {
    fetchDocuments();
  }, [fetchDocuments]);

  const handleSignDocument = (docId) => {
    if (!hasSignature) {
      alert('Please upload your signature first before signing documents.');
      navigate('/signature');
      return;
    }
    navigate(`/sign/${docId}`);
  };

  const handleDeleteDocument = async (docId) => {
    if (!window.confirm('Are you sure you want to delete this document?')) return;

    try {
      await documentAPI.delete(docId);
      fetchDocuments();
    } catch (err) {
      alert('Failed to delete document');
    }
  };

  const handleDownload = async (docId) => {
    try {
      const response = await documentAPI.downloadBlob(docId);
      const url = URL.createObjectURL(response.data);
      const doc = documents.find(d => d.id === docId);
      const a = window.document.createElement('a');
      a.href = url;
      a.download = `signed_${doc?.filename || 'document.pdf'}`;
      window.document.body.appendChild(a);
      a.click();
      window.document.body.removeChild(a);
      URL.revokeObjectURL(url);
    } catch (err) {
      console.error('Download failed:', err);
    }
  };

  // Bulk selection handlers
  const handleSelectDoc = (docId) => {
    setSelectedDocs(prev =>
      prev.includes(docId)
        ? prev.filter(id => id !== docId)
        : [...prev, docId]
    );
  };

  const handleSelectAll = () => {
    if (selectedDocs.length === documents.length) {
      setSelectedDocs([]);
    } else {
      setSelectedDocs(documents.map(d => d.id));
    }
  };

  const handleBulkSign = () => {
    if (!hasSignature) {
      alert('Please upload your signature first before signing documents.');
      navigate('/signature');
      return;
    }
    if (selectedDocs.length === 0) {
      alert('Please select at least one document to sign.');
      return;
    }
    setShowBulkModal(true);
  };

  const handleBulkSignComplete = () => {
    setShowBulkModal(false);
    setSelectedDocs([]);
    fetchDocuments();
  };

  const formatDate = (dateString) => {
    if (!dateString) return '-';
    return new Date(dateString).toLocaleDateString('en-US', {
      year: 'numeric',
      month: 'short',
      day: 'numeric',
      hour: '2-digit',
      minute: '2-digit',
    });
  };

  const pendingDocs = documents.filter(d => d.status === 'pending');

  return (
    <div className="documents-page">
      <div className="documents-header">
        <h1>Documents</h1>
        <div className="header-actions">
          {isAdmin && (
            <Link to="/upload" className="btn-upload">
              + Upload New Document
            </Link>
          )}
        </div>
      </div>

      <div className="filter-tabs">
        <button
          className={filter === 'pending' ? 'active' : ''}
          onClick={() => setFilter('pending')}
        >
          Pending ({pendingDocs.length || 0})
        </button>
        <button
          className={filter === 'signed' ? 'active' : ''}
          onClick={() => setFilter('signed')}
        >
          Signed
        </button>
      </div>

      {/* Bulk Actions Bar */}
      {filter === 'pending' && documents.length > 0 && (
        <div className="bulk-actions-bar">
          <div className="bulk-left">
            <label className="checkbox-container">
              <input
                type="checkbox"
                checked={selectedDocs.length === documents.length && documents.length > 0}
                onChange={handleSelectAll}
              />
              <span className="checkmark"></span>
              Select All ({documents.length})
            </label>
            {selectedDocs.length > 0 && (
              <span className="selected-count">{selectedDocs.length} selected</span>
            )}
          </div>
          <div className="bulk-right">
            <label className="auto-mode-toggle">
              <input
                type="checkbox"
                checked={autoMode}
                onChange={(e) => setAutoMode(e.target.checked)}
              />
              <span className="toggle-slider"></span>
              Full Auto Mode
            </label>
            <button
              className="btn-bulk-sign"
              onClick={handleBulkSign}
              disabled={selectedDocs.length === 0}
            >
              Bulk Sign ({selectedDocs.length})
            </button>
          </div>
        </div>
      )}

      {error && <div className="error-message">{error}</div>}

      {loading ? (
        <div className="loading">Loading documents...</div>
      ) : documents.length === 0 ? (
        <div className="empty-state">
          <div className="empty-icon">📄</div>
          <h3>No {filter} documents</h3>
          <p>
            {filter === 'pending'
              ? 'All documents have been signed or no documents uploaded yet.'
              : 'No signed documents yet.'}
          </p>
        </div>
      ) : (
        <div className="documents-table">
          <table>
            <thead>
              <tr>
                {filter === 'pending' && <th className="th-checkbox"></th>}
                <th>Document</th>
                <th>Type</th>
                <th>Patient</th>
                <th>Uploaded</th>
                {filter === 'signed' && <th>Signed By</th>}
                {filter === 'signed' && <th>Signed At</th>}
                <th>Actions</th>
              </tr>
            </thead>
            <tbody>
              {documents.map((doc) => (
                <tr key={doc.id} className={selectedDocs.includes(doc.id) ? 'selected' : ''}>
                  {filter === 'pending' && (
                    <td className="td-checkbox">
                      <label className="checkbox-container small">
                        <input
                          type="checkbox"
                          checked={selectedDocs.includes(doc.id)}
                          onChange={() => handleSelectDoc(doc.id)}
                        />
                        <span className="checkmark"></span>
                      </label>
                    </td>
                  )}
                  <td className="doc-name">
                    <span className="file-icon">📄</span>
                    {doc.filename}
                  </td>
                  <td>
                    <span className="doc-type">{doc.document_type || 'General'}</span>
                  </td>
                  <td>{doc.patient_name || '-'}</td>
                  <td>{formatDate(doc.uploaded_at)}</td>
                  {filter === 'signed' && <td>{doc.signed_by}</td>}
                  {filter === 'signed' && <td>{formatDate(doc.signed_at)}</td>}
                  <td className="actions">
                    {filter === 'pending' ? (
                      <>
                        <button
                          className="btn-action btn-sign"
                          onClick={() => handleSignDocument(doc.id)}
                        >
                          Sign
                        </button>
                        {isAdmin && (
                          <button
                            className="btn-action btn-delete"
                            onClick={() => handleDeleteDocument(doc.id)}
                          >
                            Delete
                          </button>
                        )}
                      </>
                    ) : (
                      <>
                        <button
                          className="btn-action btn-view"
                          onClick={() => navigate(`/view/${doc.id}`)}
                        >
                          View
                        </button>
                        <button
                          className="btn-action btn-download"
                          onClick={() => handleDownload(doc.id)}
                        >
                          Download
                        </button>
                      </>
                    )}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}

      {/* Bulk Sign Modal */}
      {showBulkModal && (
        <BulkSignModal
          documentIds={selectedDocs}
          documents={documents.filter(d => selectedDocs.includes(d.id))}
          autoMode={autoMode}
          onClose={() => setShowBulkModal(false)}
          onComplete={handleBulkSignComplete}
        />
      )}
    </div>
  );
};

export default Documents;
