import React, { useState, useEffect, useCallback } from 'react';
import { documentAPI } from '../services/api';
import DocumentPreviewModal from './DocumentPreviewModal';
import './BulkSignModal.css';

const BulkSignModal = ({ documentIds, documents, autoMode, onClose, onComplete }) => {
  const [step, setStep] = useState('detecting'); // detecting, preview, signing, complete
  const [detectionResults, setDetectionResults] = useState([]);
  const [signedCount, setSignedCount] = useState(0);
  const [errors, setErrors] = useState([]);
  const [currentDoc, setCurrentDoc] = useState(0);

  // Preview state
  const [previewDoc, setPreviewDoc] = useState(null);

  // Detect signature positions for all documents
  const detectPositions = useCallback(async () => {
    const results = [];

    for (let i = 0; i < documentIds.length; i++) {
      const docId = documentIds[i];
      const doc = documents.find(d => d.id === docId);

      setCurrentDoc(i + 1);

      try {
        const response = await documentAPI.detectSignaturePosition(docId);
        results.push({
          id: docId,
          filename: doc?.filename || `Document ${docId}`,
          detection: response.data,
          selected: response.data.found,
          edited: false,
        });
      } catch (err) {
        results.push({
          id: docId,
          filename: doc?.filename || `Document ${docId}`,
          detection: { found: false },
          selected: false,
          error: 'Detection failed',
          edited: false,
        });
      }
    }

    setDetectionResults(results);

    if (autoMode) {
      // In auto mode, proceed directly to signing
      setStep('signing');
    } else {
      // In manual mode, show preview for approval
      setStep('preview');
    }
  }, [documentIds, documents, autoMode]);

  // Start detection on mount
  useEffect(() => {
    detectPositions();
  }, [detectPositions]);

  // Sign all selected documents
  const handleSign = async () => {
    setStep('signing');
    setSignedCount(0);
    setErrors([]);

    const docsToSign = detectionResults
      .filter(r => r.selected && (r.detection.found || r.edited))
      .map(r => {
        // Support both new positions array format and old direct properties
        let positions = [];
        if (r.detection.positions && r.detection.positions.length > 0) {
          positions = r.detection.positions;
        } else if (r.detection.x !== undefined) {
          // Old format - convert to positions array
          positions = [{
            x: r.detection.x,
            y: r.detection.y,
            page: r.detection.page,
            width: r.detection.width,
            height: r.detection.height,
          }];
        }
        return {
          id: r.id,
          positions: positions,
          // Keep single position for backward compat
          position: positions[0] || null,
        };
      });

    if (docsToSign.length === 0) {
      setErrors([{ message: 'No documents selected for signing' }]);
      setStep('complete');
      return;
    }

    try {
      const response = await documentAPI.bulkSign(docsToSign, autoMode);
      // Backend returns { results: { successful: [], failed: [] } }
      const results = response.data.results || {};
      setSignedCount(results.successful?.length || 0);
      if (results.failed && results.failed.length > 0) {
        setErrors(results.failed);
      }
    } catch (err) {
      setErrors([{ message: err.response?.data?.error || 'Bulk signing failed' }]);
    }

    setStep('complete');
  };

  // Toggle document selection
  const toggleDocSelection = (docId, e) => {
    if (e) e.stopPropagation();
    setDetectionResults(prev =>
      prev.map(r =>
        r.id === docId ? { ...r, selected: !r.selected } : r
      )
    );
  };

  // Open preview for a document
  const openPreview = (result) => {
    setPreviewDoc(result);
  };

  // Save position from preview
  const handleSavePosition = (docId, newPosition) => {
    setDetectionResults(prev =>
      prev.map(r =>
        r.id === docId
          ? {
              ...r,
              detection: {
                ...r.detection,
                ...newPosition,
              },
              selected: true,
              edited: true,
            }
          : r
      )
    );
    setPreviewDoc(null);
  };

  // Auto-proceed in auto mode after detection
  useEffect(() => {
    if (step === 'signing' && autoMode && detectionResults.length > 0) {
      handleSign();
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [step, autoMode, detectionResults.length]);

  const getConfidenceClass = (confidence) => {
    return confidence || 'low';
  };

  // Helper to get first position from detection (supports both old and new format)
  const getFirstPosition = (detection) => {
    if (!detection) return null;
    if (detection.positions && detection.positions.length > 0) {
      return detection.positions[0];
    }
    // Old format - detection has properties directly
    if (detection.x !== undefined) {
      return detection;
    }
    return null;
  };

  const selectedCount = detectionResults.filter(r => r.selected).length;
  const detectedCount = detectionResults.filter(r => r.detection.found).length;

  return (
    <div className="bulk-modal-overlay">
      <div className="bulk-modal">
        <div className="bulk-modal-header">
          <h2>
            {step === 'detecting' && 'Detecting Signature Positions...'}
            {step === 'preview' && 'Review Documents'}
            {step === 'signing' && 'Signing Documents...'}
            {step === 'complete' && 'Signing Complete'}
          </h2>
          {step !== 'signing' && (
            <button className="btn-close" onClick={onClose}>×</button>
          )}
        </div>

        <div className="bulk-modal-content">
          {/* Detecting Phase */}
          {step === 'detecting' && (
            <div className="detecting-phase">
              <div className="progress-spinner"></div>
              <p>Analyzing document {currentDoc} of {documentIds.length}...</p>
              <div className="progress-bar">
                <div
                  className="progress-fill"
                  style={{ width: `${(currentDoc / documentIds.length) * 100}%` }}
                ></div>
              </div>
            </div>
          )}

          {/* Preview Phase */}
          {step === 'preview' && (
            <div className="preview-phase">
              <div className="preview-summary">
                <p>
                  Found signature positions in <strong>{detectedCount}</strong> of{' '}
                  <strong>{documentIds.length}</strong> documents.
                </p>
                <p className="preview-hint">
                  Click on a document to preview and edit signature position.
                </p>
              </div>

              <div className="document-list">
                {detectionResults.map((result) => (
                  <div
                    key={result.id}
                    className={`document-item ${result.selected ? 'selected' : ''} ${!result.detection.found && !result.edited ? 'no-detection' : ''}`}
                  >
                    <div className="doc-checkbox" onClick={(e) => e.stopPropagation()}>
                      <input
                        type="checkbox"
                        checked={result.selected}
                        onChange={(e) => toggleDocSelection(result.id, e)}
                        disabled={!result.detection.found && !result.edited}
                      />
                    </div>
                    <div
                      className="doc-info clickable"
                      onClick={() => openPreview(result)}
                    >
                      <span className="doc-name">{result.filename}</span>
                      {result.detection.found || result.edited ? (
                        <span className={`confidence-badge ${result.edited ? 'edited' : getConfidenceClass(getFirstPosition(result.detection)?.confidence)}`}>
                          {result.edited ? 'manually edited' : (() => {
                            const pos = getFirstPosition(result.detection);
                            const posCount = result.detection.positions?.length || 1;
                            return posCount > 1
                              ? `${posCount} signatures`
                              : `${pos?.confidence || 'detected'} confidence`;
                          })()}
                          {getFirstPosition(result.detection)?.keyword && !result.edited && ` • "${getFirstPosition(result.detection).keyword}"`}
                        </span>
                      ) : (
                        <span className="no-detection-text">
                          {result.error || 'Click to set position manually'}
                        </span>
                      )}
                    </div>
                    <div className="doc-actions">
                      <button
                        className="btn-preview"
                        onClick={(e) => { e.stopPropagation(); openPreview(result); }}
                        title="Preview & Edit"
                      >
                        <span className="preview-icon">👁</span>
                      </button>
                      <div className="doc-status">
                        {result.detection.found || result.edited ? (
                          <span className="status-icon found">✓</span>
                        ) : (
                          <span className="status-icon not-found">✗</span>
                        )}
                      </div>
                    </div>
                  </div>
                ))}
              </div>
            </div>
          )}

          {/* Signing Phase */}
          {step === 'signing' && (
            <div className="signing-phase">
              <div className="progress-spinner"></div>
              <p>Signing {selectedCount} documents...</p>
              <p className="signing-hint">Please wait, this may take a moment.</p>
            </div>
          )}

          {/* Complete Phase */}
          {step === 'complete' && (
            <div className="complete-phase">
              <div className={`complete-icon ${errors.length > 0 ? 'has-errors' : ''}`}>
                {errors.length === 0 ? '✓' : '⚠'}
              </div>
              <h3>
                {signedCount > 0
                  ? `Successfully signed ${signedCount} document${signedCount !== 1 ? 's' : ''}`
                  : 'No documents were signed'}
              </h3>

              {errors.length > 0 && (
                <div className="error-list">
                  <p className="error-title">Some documents could not be signed:</p>
                  {errors.map((err, idx) => (
                    <div key={idx} className="error-item">
                      {err.document_id && <strong>Document {err.document_id}: </strong>}
                      {err.error || err.message}
                    </div>
                  ))}
                </div>
              )}
            </div>
          )}
        </div>

        <div className="bulk-modal-footer">
          {step === 'preview' && (
            <>
              <button className="btn-secondary" onClick={onClose}>
                Cancel
              </button>
              <button
                className="btn-primary"
                onClick={handleSign}
                disabled={selectedCount === 0}
              >
                Sign {selectedCount} Document{selectedCount !== 1 ? 's' : ''}
              </button>
            </>
          )}

          {step === 'complete' && (
            <button
              className="btn-primary"
              onClick={() => {
                onComplete(signedCount);
                onClose();
              }}
            >
              Done
            </button>
          )}
        </div>
      </div>

      {/* Document Preview Modal */}
      {previewDoc && (
        <DocumentPreviewModal
          docId={previewDoc.id}
          filename={previewDoc.filename}
          detection={previewDoc.detection}
          onClose={() => setPreviewDoc(null)}
          onSave={(newPosition) => handleSavePosition(previewDoc.id, newPosition)}
          isF2F={previewDoc.detection?.is_f2f || false}
        />
      )}
    </div>
  );
};

export default BulkSignModal;
