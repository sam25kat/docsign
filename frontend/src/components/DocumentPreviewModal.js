import React, { useState, useEffect, useRef, useCallback } from 'react';
import { Document, Page, pdfjs } from 'react-pdf';
import { documentAPI, signatureAPI } from '../services/api';
import 'react-pdf/dist/esm/Page/AnnotationLayer.css';
import 'react-pdf/dist/esm/Page/TextLayer.css';
import './DocumentPreviewModal.css';

pdfjs.GlobalWorkerOptions.workerSrc = `//cdnjs.cloudflare.com/ajax/libs/pdf.js/${pdfjs.version}/pdf.worker.min.js`;

const DocumentPreviewModal = ({
  docId,
  filename,
  detection,
  onClose,
  onSave,
  isF2F = false
}) => {
  const [pdfUrl, setPdfUrl] = useState(null);
  const [numPages, setNumPages] = useState(null);
  const [currentPage, setCurrentPage] = useState(1);
  const [scale, setScale] = useState(1.0);
  const [signaturePreview, setSignaturePreview] = useState(null);
  const [signerName, setSignerName] = useState('');
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');

  // Signature positions state - supports multiple (one per page max)
  const [signaturePositions, setSignaturePositions] = useState([]);
  const [isDragging, setIsDragging] = useState(false);
  const [dragOffset, setDragOffset] = useState({ x: 0, y: 0 });

  const pageContainerRef = useRef(null);
  const signatureRef = useRef(null);

  // Load PDF and signature
  useEffect(() => {
    const loadData = async () => {
      try {
        // Fetch PDF
        const fileResponse = await documentAPI.getFile(docId);
        const blobUrl = URL.createObjectURL(fileResponse.data);
        setPdfUrl(blobUrl);

        // Fetch signature and signer name
        const sigResponse = await signatureAPI.preview();
        setSignaturePreview(sigResponse.data.signature);
        setSignerName(sigResponse.data.info?.signer_name || '');

        // Initialize positions from detection (supports both old and new format)
        if (detection && detection.found) {
          if (detection.positions && detection.positions.length > 0) {
            // New format: positions array
            setSignaturePositions(detection.positions.map(pos => ({
              x: pos.x,
              y: pos.y,
              page: pos.page,
              width: pos.width || 120,
              height: pos.height || 40,
            })));
            // Navigate to first detected page
            setCurrentPage(detection.positions[0].page + 1);
          } else {
            // Old format: direct properties (backward compat)
            setSignaturePositions([{
              x: detection.x,
              y: detection.y,
              page: detection.page,
              width: detection.width || 120,
              height: detection.height || 40,
            }]);
            setCurrentPage(detection.page + 1);
          }
        }
      } catch (err) {
        setError('Failed to load document');
        console.error(err);
      } finally {
        setLoading(false);
      }
    };

    loadData();

    // Cleanup
    return () => {
      if (pdfUrl && pdfUrl.startsWith('blob:')) {
        URL.revokeObjectURL(pdfUrl);
      }
    };
  }, [docId, detection]);

  const onDocumentLoadSuccess = ({ numPages: totalPages }) => {
    setNumPages(totalPages);
  };

  // Get current page's signature position
  const currentPagePosition = signaturePositions.find(p => p.page === currentPage - 1);

  // Place signature on click (one per page max)
  const handlePageClick = (e) => {
    if (!signaturePreview) return;
    if (e.target.closest('.signature-overlay')) return;
    // Don't place if current page already has a signature
    if (currentPagePosition) return;

    const container = pageContainerRef.current;
    if (!container) return;

    const rect = container.getBoundingClientRect();
    const x = (e.clientX - rect.left) / scale;
    const y = (e.clientY - rect.top) / scale;

    const newPosition = {
      x: Math.max(0, x - 60),
      y: Math.max(0, y - 20),
      page: currentPage - 1,
      width: 120,
      height: 40,
    };

    setSignaturePositions(prev => [...prev, newPosition]);
  };

  // Drag handlers
  const handleDragStart = (e) => {
    if (!currentPagePosition) return;

    e.preventDefault();
    e.stopPropagation();
    const rect = signatureRef.current.getBoundingClientRect();
    setDragOffset({
      x: e.clientX - rect.left,
      y: e.clientY - rect.top,
    });
    setIsDragging(true);
  };

  const handleDragMove = useCallback((e) => {
    if (!isDragging || !pageContainerRef.current || !currentPagePosition) return;

    const container = pageContainerRef.current;
    const rect = container.getBoundingClientRect();

    const newX = (e.clientX - rect.left - dragOffset.x) / scale;
    const newY = (e.clientY - rect.top - dragOffset.y) / scale;

    const maxX = (rect.width / scale) - currentPagePosition.width;
    const maxY = (rect.height / scale) - currentPagePosition.height;

    setSignaturePositions(prev => prev.map(p =>
      p.page === currentPage - 1
        ? { ...p, x: Math.max(0, Math.min(newX, maxX)), y: Math.max(0, Math.min(newY, maxY)) }
        : p
    ));
  }, [isDragging, dragOffset, scale, currentPagePosition, currentPage]);

  const handleDragEnd = () => {
    setIsDragging(false);
  };

  // Add/remove event listeners for dragging
  useEffect(() => {
    if (isDragging) {
      window.addEventListener('mousemove', handleDragMove);
      window.addEventListener('mouseup', handleDragEnd);
    }
    return () => {
      window.removeEventListener('mousemove', handleDragMove);
      window.removeEventListener('mouseup', handleDragEnd);
    };
  }, [isDragging, handleDragMove]);

  // Resize signature on current page
  const handleResize = (newWidth) => {
    if (!currentPagePosition) return;
    const aspectRatio = currentPagePosition.height / currentPagePosition.width;
    setSignaturePositions(prev => prev.map(p =>
      p.page === currentPage - 1
        ? { ...p, width: newWidth, height: newWidth * aspectRatio }
        : p
    ));
  };

  // Clear signature position on current page
  const handleClearPosition = () => {
    setSignaturePositions(prev => prev.filter(p => p.page !== currentPage - 1));
  };

  // Save and close
  const handleSave = () => {
    if (signaturePositions.length > 0) {
      // Return positions in a format compatible with both old and new handling
      onSave({
        found: true,
        positions: signaturePositions,
        // Also include first position's data for backward compatibility
        ...(signaturePositions[0] || {}),
      });
    }
    onClose();
  };

  // Navigation
  const goToPrevPage = () => {
    if (currentPage > 1) {
      setCurrentPage(currentPage - 1);
    }
  };

  const goToNextPage = () => {
    if (numPages && currentPage < numPages) {
      setCurrentPage(currentPage + 1);
    }
  };

  return (
    <div className="preview-modal-overlay" onClick={onClose}>
      <div className="preview-modal" onClick={(e) => e.stopPropagation()}>
        <div className="preview-modal-header">
          <div className="preview-title">
            <h2>Preview & Edit Position</h2>
            <span className="preview-filename">{filename}</span>
          </div>
          <button className="btn-close" onClick={onClose}>×</button>
        </div>

        <div className="preview-modal-content">
          {loading ? (
            <div className="preview-loading">
              <div className="progress-spinner"></div>
              <p>Loading document...</p>
            </div>
          ) : error ? (
            <div className="preview-error">
              <p>{error}</p>
            </div>
          ) : (
            <>
              <div className="preview-toolbar">
                <div className="toolbar-group">
                  <button onClick={goToPrevPage} disabled={currentPage <= 1}>←</button>
                  <span>Page {currentPage} / {numPages || '...'}</span>
                  <button onClick={goToNextPage} disabled={!numPages || currentPage >= numPages}>→</button>
                </div>

                <div className="toolbar-group">
                  <button onClick={() => setScale(s => Math.max(0.5, s - 0.1))}>−</button>
                  <span>{Math.round(scale * 100)}%</span>
                  <button onClick={() => setScale(s => Math.min(2, s + 0.1))}>+</button>
                </div>

                {currentPagePosition && (
                  <div className="toolbar-group">
                    <label>Size:</label>
                    <input
                      type="range"
                      min="60"
                      max="250"
                      value={currentPagePosition.width}
                      onChange={(e) => handleResize(Number(e.target.value))}
                    />
                    <button className="btn-clear" onClick={handleClearPosition}>
                      Remove
                    </button>
                  </div>
                )}
              </div>

              <div className="preview-instructions">
                {signaturePositions.length === 0 ? (
                  <p>Click anywhere on the document to place your signature</p>
                ) : (
                  <p>
                    {currentPagePosition
                      ? 'Drag to move • Use slider to resize'
                      : 'Click to place signature on this page'}
                    {' • '}{signaturePositions.length} page(s) have signatures
                  </p>
                )}
              </div>

              <div className="preview-pdf-area">
                <div
                  className={`preview-page-container ${!currentPagePosition ? 'placing-mode' : ''}`}
                  ref={pageContainerRef}
                  onClick={handlePageClick}
                >
                  <Document file={pdfUrl} onLoadSuccess={onDocumentLoadSuccess}>
                    <Page pageNumber={currentPage} scale={scale} />
                  </Document>

                  {currentPagePosition && (
                    <div
                      ref={signatureRef}
                      className={`signature-overlay ${isDragging ? 'dragging' : ''} ${isF2F ? 'f2f-signature' : ''}`}
                      style={{
                        left: currentPagePosition.x * scale,
                        top: currentPagePosition.y * scale,
                        width: isF2F ? 280 * scale : currentPagePosition.width * scale,
                      }}
                      onMouseDown={handleDragStart}
                    >
                      {isF2F ? (
                        /* F2F Electronic Signature Box Preview */
                        <div className="f2f-signature-box" style={{ transform: `scale(${scale})`, transformOrigin: 'top left' }}>
                          <div className="f2f-header">Electronic Signature</div>
                          <div className="f2f-sig-area">
                            <img
                              src={signaturePreview}
                              alt="Your signature"
                              draggable={false}
                            />
                          </div>
                          <div className="f2f-info">
                            <div className="f2f-row">
                              <span className="f2f-label">Document ID:</span>
                            </div>
                            <div className="f2f-row">
                              <span className="f2f-value-blue">xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx</span>
                            </div>
                            <div className="f2f-row">
                              <span className="f2f-label">IP Address: ::1</span>
                            </div>
                            <div className="f2f-row">
                              <span className="f2f-label">Time: {new Date().toLocaleString('en-US', { weekday: 'long', day: '2-digit', month: 'long', year: 'numeric', hour: '2-digit', minute: '2-digit', second: '2-digit' })}</span>
                            </div>
                            <div className="f2f-row">
                              <span className="f2f-label">Signer: </span>
                              <span className="f2f-value-blue">{signerName || 'Unknown'}</span>
                            </div>
                          </div>
                          <div className="f2f-qr-placeholder"></div>
                        </div>
                      ) : (
                        /* Regular Signature Preview */
                        <>
                          <img
                            src={signaturePreview}
                            alt="Your signature"
                            draggable={false}
                            style={{
                              width: '100%',
                              height: currentPagePosition.height * scale,
                              objectFit: 'contain'
                            }}
                          />
                          {signerName && (
                            <div className="signature-text-preview" style={{ fontSize: `${7 * scale}px` }}>
                              <span>Digitally signed by</span>
                              <strong>{signerName}</strong>
                              <span>Date: {new Date().toLocaleString()}</span>
                            </div>
                          )}
                        </>
                      )}
                      <div className="drag-hint">Drag to move</div>
                    </div>
                  )}
                </div>
              </div>
            </>
          )}
        </div>

        <div className="preview-modal-footer">
          <button className="btn-secondary" onClick={onClose}>
            Cancel
          </button>
          <button
            className="btn-primary"
            onClick={handleSave}
            disabled={signaturePositions.length === 0}
          >
            Save Position{signaturePositions.length > 1 ? 's' : ''}
          </button>
        </div>
      </div>
    </div>
  );
};

export default DocumentPreviewModal;
