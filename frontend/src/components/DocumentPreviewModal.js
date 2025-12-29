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
  onSave
}) => {
  const [pdfUrl, setPdfUrl] = useState(null);
  const [numPages, setNumPages] = useState(null);
  const [currentPage, setCurrentPage] = useState(1);
  const [scale, setScale] = useState(1.0);
  const [signaturePreview, setSignaturePreview] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');

  // Signature position state - initialize from detection
  const [signaturePosition, setSignaturePosition] = useState(null);
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

        // Fetch signature
        const sigResponse = await signatureAPI.preview();
        setSignaturePreview(sigResponse.data.signature);

        // Initialize position from detection
        if (detection && detection.found) {
          setSignaturePosition({
            x: detection.x,
            y: detection.y,
            page: detection.page,
            width: detection.width || 120,
            height: detection.height || 40,
          });
          setCurrentPage(detection.page + 1);
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

  // Place signature on click
  const handlePageClick = (e) => {
    if (!signaturePreview || signaturePosition) return;
    if (e.target.closest('.signature-overlay')) return;

    const container = pageContainerRef.current;
    if (!container) return;

    const rect = container.getBoundingClientRect();
    const x = (e.clientX - rect.left) / scale;
    const y = (e.clientY - rect.top) / scale;

    setSignaturePosition({
      x: Math.max(0, x - 60),
      y: Math.max(0, y - 20),
      page: currentPage - 1,
      width: 120,
      height: 40,
    });
  };

  // Drag handlers
  const handleDragStart = (e) => {
    if (!signaturePosition) return;

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
    if (!isDragging || !pageContainerRef.current) return;

    const container = pageContainerRef.current;
    const rect = container.getBoundingClientRect();

    const newX = (e.clientX - rect.left - dragOffset.x) / scale;
    const newY = (e.clientY - rect.top - dragOffset.y) / scale;

    const maxX = (rect.width / scale) - signaturePosition.width;
    const maxY = (rect.height / scale) - signaturePosition.height;

    setSignaturePosition(prev => ({
      ...prev,
      x: Math.max(0, Math.min(newX, maxX)),
      y: Math.max(0, Math.min(newY, maxY)),
    }));
  }, [isDragging, dragOffset, scale, signaturePosition?.width, signaturePosition?.height]);

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

  // Resize signature
  const handleResize = (newWidth) => {
    const aspectRatio = signaturePosition.height / signaturePosition.width;
    setSignaturePosition(prev => ({
      ...prev,
      width: newWidth,
      height: newWidth * aspectRatio,
    }));
  };

  // Clear signature position
  const handleClearPosition = () => {
    setSignaturePosition(null);
  };

  // Save and close
  const handleSave = () => {
    if (signaturePosition) {
      onSave({
        ...signaturePosition,
        found: true,
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

                {signaturePosition && (
                  <div className="toolbar-group">
                    <label>Size:</label>
                    <input
                      type="range"
                      min="60"
                      max="250"
                      value={signaturePosition.width}
                      onChange={(e) => handleResize(Number(e.target.value))}
                    />
                    <button className="btn-clear" onClick={handleClearPosition}>
                      Remove
                    </button>
                  </div>
                )}
              </div>

              <div className="preview-instructions">
                {!signaturePosition ? (
                  <p>Click anywhere on the document to place your signature</p>
                ) : (
                  <p>Drag to move • Use slider to resize • Click "Save Position" when done</p>
                )}
              </div>

              <div className="preview-pdf-area">
                <div
                  className={`preview-page-container ${!signaturePosition ? 'placing-mode' : ''}`}
                  ref={pageContainerRef}
                  onClick={handlePageClick}
                >
                  <Document file={pdfUrl} onLoadSuccess={onDocumentLoadSuccess}>
                    <Page pageNumber={currentPage} scale={scale} />
                  </Document>

                  {signaturePosition && signaturePosition.page === currentPage - 1 && (
                    <div
                      ref={signatureRef}
                      className={`signature-overlay ${isDragging ? 'dragging' : ''}`}
                      style={{
                        left: signaturePosition.x * scale,
                        top: signaturePosition.y * scale,
                        width: signaturePosition.width * scale,
                        height: signaturePosition.height * scale,
                      }}
                      onMouseDown={handleDragStart}
                    >
                      <img src={signaturePreview} alt="Your signature" draggable={false} />
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
            disabled={!signaturePosition}
          >
            Save Position
          </button>
        </div>
      </div>
    </div>
  );
};

export default DocumentPreviewModal;
