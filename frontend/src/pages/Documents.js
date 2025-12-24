import React, { useState, useEffect, useCallback } from 'react';
import { Link, useNavigate } from 'react-router-dom';
import { documentAPI } from '../services/api';
import { useAuth } from '../context/AuthContext';
import './Documents.css';

const Documents = () => {
  const [documents, setDocuments] = useState([]);
  const [filter, setFilter] = useState('pending');
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');
  const { isAdmin, hasSignature } = useAuth();
  const navigate = useNavigate();

  const fetchDocuments = useCallback(async () => {
    setLoading(true);
    try {
      const response = await documentAPI.list(filter);
      setDocuments(response.data);
      setError('');
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

  const handleDownload = (docId) => {
    window.open(documentAPI.download(docId), '_blank');
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

  return (
    <div className="documents-page">
      <div className="documents-header">
        <h1>Documents</h1>
        {isAdmin && (
          <Link to="/upload" className="btn-upload">
            + Upload New Document
          </Link>
        )}
      </div>

      <div className="filter-tabs">
        <button
          className={filter === 'pending' ? 'active' : ''}
          onClick={() => setFilter('pending')}
        >
          Pending ({documents.filter(d => d.status === 'pending').length || '...'})
        </button>
        <button
          className={filter === 'signed' ? 'active' : ''}
          onClick={() => setFilter('signed')}
        >
          Signed
        </button>
      </div>

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
                <tr key={doc.id}>
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
    </div>
  );
};

export default Documents;
