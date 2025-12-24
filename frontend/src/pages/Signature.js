import React, { useState, useEffect } from 'react';
import { signatureAPI } from '../services/api';
import SignatureUpload from '../components/SignatureUpload';
import { useAuth } from '../context/AuthContext';
import './Signature.css';

const Signature = () => {
  const [signaturePreview, setSignaturePreview] = useState(null);
  const [loading, setLoading] = useState(true);
  const [deleting, setDeleting] = useState(false);
  const { checkAuth } = useAuth();

  useEffect(() => {
    loadSignature();
  }, []);

  const loadSignature = async () => {
    setLoading(true);
    try {
      const response = await signatureAPI.preview();
      setSignaturePreview(response.data.signature);
    } catch (err) {
      // No signature found
      setSignaturePreview(null);
    } finally {
      setLoading(false);
    }
  };

  const handleUploadSuccess = () => {
    loadSignature();
    checkAuth(); // Update user's has_signature status
  };

  const handleDelete = async () => {
    if (!window.confirm('Are you sure you want to delete your signature? You will need to upload a new one to sign documents.')) {
      return;
    }

    setDeleting(true);
    try {
      await signatureAPI.delete();
      setSignaturePreview(null);
      checkAuth();
    } catch (err) {
      alert('Failed to delete signature');
    } finally {
      setDeleting(false);
    }
  };

  if (loading) {
    return (
      <div className="signature-page">
        <div className="loading">Loading signature...</div>
      </div>
    );
  }

  return (
    <div className="signature-page">
      <div className="signature-container">
        <h1>My Signature</h1>
        <p className="page-subtitle">
          Your signature is securely stored and encrypted. It will be used to sign medical documents.
        </p>

        {signaturePreview ? (
          <div className="current-signature-section">
            <div className="signature-card">
              <h3>Current Signature</h3>
              <div className="signature-display">
                <img src={signaturePreview} alt="Your signature" />
              </div>
              <p className="signature-info">
                Background has been automatically removed for clean document signing.
              </p>
              <div className="signature-actions">
                <button className="btn-delete" onClick={handleDelete} disabled={deleting}>
                  {deleting ? 'Deleting...' : 'Delete Signature'}
                </button>
              </div>
            </div>

            <div className="update-section">
              <h3>Update Signature</h3>
              <p>Upload a new signature image to replace the current one.</p>
              <SignatureUpload onUploadSuccess={handleUploadSuccess} />
            </div>
          </div>
        ) : (
          <div className="no-signature-section">
            <div className="no-signature-message">
              <div className="icon">✍️</div>
              <h3>No Signature Uploaded</h3>
              <p>Upload your signature to start signing documents.</p>
            </div>
            <SignatureUpload onUploadSuccess={handleUploadSuccess} />
          </div>
        )}

        <div className="security-info">
          <h3>🔒 Security Information</h3>
          <ul>
            <li><strong>Encrypted Storage:</strong> Your signature is encrypted using AES-256 encryption</li>
            <li><strong>Background Removal:</strong> We automatically remove the background for clean signing</li>
            <li><strong>Integrity Verification:</strong> SHA-256 hash ensures your signature hasn't been tampered with</li>
            <li><strong>Secure Access:</strong> Only you can access and use your signature</li>
          </ul>
        </div>
      </div>
    </div>
  );
};

export default Signature;
