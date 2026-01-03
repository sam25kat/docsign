import React, { useState, useEffect, useRef, useCallback } from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import { Document, Page, pdfjs } from 'react-pdf';
import { documentAPI, signatureAPI } from '../services/api';
import 'react-pdf/dist/esm/Page/AnnotationLayer.css';
import 'react-pdf/dist/esm/Page/TextLayer.css';
import './SignDocument.css';

pdfjs.GlobalWorkerOptions.workerSrc = `//cdnjs.cloudflare.com/ajax/libs/pdf.js/${pdfjs.version}/pdf.worker.min.js`;

const SignDocument = () => {
  const { id } = useParams();
  const navigate = useNavigate();

  const [document, setDocument] = useState(null);
  const [pdfUrl, setPdfUrl] = useState(null);
  const [numPages, setNumPages] = useState(null);
  const [currentPage, setCurrentPage] = useState(1);
  const [scale, setScale] = useState(1.0);
  const [signaturePreview, setSignaturePreview] = useState(null);
  const [loading, setLoading] = useState(true);
  const [signing, setSigning] = useState(false);
  const [error, setError] = useState('');
  const [detecting, setDetecting] = useState(false);
  const [detectionInfo, setDetectionInfo] = useState(null);
  const [isF2F, setIsF2F] = useState(false);
  const [signerName, setSignerName] = useState('');

  // Signature positions state - supports multiple positions (one per page max)
  const [signaturePositions, setSignaturePositions] = useState([]); // All positions
  const [isDragging, setIsDragging] = useState(false);
  const [dragOffset, setDragOffset] = useState({ x: 0, y: 0 });

  const pageContainerRef = useRef(null);
  const signatureRef = useRef(null);

  const loadDocument = useCallback(async () => {
    try {
      const response = await documentAPI.get(id);
      setDocument(response.data.document);

      // Check if F2F document
      if (response.data.document?.document_type === 'f2f') {
        setIsF2F(true);
      }

      // Fetch PDF as blob with credentials
      const fileResponse = await documentAPI.getFile(id);
      const blobUrl = URL.createObjectURL(fileResponse.data);
      setPdfUrl(blobUrl);
    } catch (err) {
      setError('Failed to load document');
    } finally {
      setLoading(false);
    }
  }, [id]);

  // Cleanup blob URL on unmount
  useEffect(() => {
    return () => {
      if (pdfUrl && pdfUrl.startsWith('blob:')) {
        URL.revokeObjectURL(pdfUrl);
      }
    };
  }, [pdfUrl]);

  const loadSignature = async () => {
    try {
      const response = await signatureAPI.preview();
      setSignaturePreview(response.data.signature);
      setSignerName(response.data.info?.signer_name || '');
    } catch (err) {
      setError('No signature found. Please upload your signature first.');
    }
  };

  // Load document and signature
  useEffect(() => {
    loadDocument();
    loadSignature();
  }, [loadDocument]);

  const onDocumentLoadSuccess = ({ numPages: totalPages }) => {
    setNumPages(totalPages);
  };

  // Get current page's signature position
  const currentPagePosition = signaturePositions.find(p => p.page === currentPage - 1);

  // Place signature on click (one per page max)
  const handlePageClick = (e) => {
    // Don't place if no signature loaded
    if (!signaturePreview) return;
    // Don't place if clicking on signature overlay
    if (e.target.closest('.signature-overlay')) return;
    // Don't place if current page already has a signature
    if (currentPagePosition) return;

    const container = pageContainerRef.current;
    if (!container) return;

    const rect = container.getBoundingClientRect();
    const x = (e.clientX - rect.left) / scale;
    const y = (e.clientY - rect.top) / scale;

    const newPosition = {
      x: Math.max(0, x - 75), // Center signature on click
      y: Math.max(0, y - 25),
      page: currentPage - 1,
      width: 150,
      height: 50,
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

    // Keep within bounds
    const maxX = (rect.width / scale) - currentPagePosition.width;
    const maxY = (rect.height / scale) - currentPagePosition.height;

    // Update position in the array
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

  // Clear ALL signature positions
  const handleClearAllPositions = () => {
    setSignaturePositions([]);
    setDetectionInfo(null);
  };

  // Auto-detect signature positions (multi-page)
  const handleAutoDetect = async () => {
    setDetecting(true);
    setDetectionInfo(null);

    try {
      const response = await documentAPI.detectSignaturePosition(id);
      const detection = response.data;

      if (detection.found && detection.positions && detection.positions.length > 0) {
        // Set all detected positions
        setSignaturePositions(detection.positions);

        // Navigate to the first detected page
        const firstPos = detection.positions[0];
        setCurrentPage(firstPos.page + 1);

        setDetectionInfo({
          confidence: firstPos.confidence,
          method: firstPos.method,
          keyword: firstPos.keyword,
          total: detection.positions.length,
          totalPages: detection.total_pages,
        });

        if (detection.positions.length > 1) {
          alert(`Found ${detection.positions.length} signature locations across the document.`);
        }
      } else {
        alert('Could not detect signature positions. Please place manually.');
      }
    } catch (err) {
      console.error('Detection failed:', err);
      alert('Auto-detection failed. Please place signature manually.');
    } finally {
      setDetecting(false);
    }
  };

  // Sign document (with all positions)
  const handleSign = async () => {
    if (signaturePositions.length === 0) {
      alert('Please place your signature on the document first.');
      return;
    }

    setSigning(true);
    try {
      await documentAPI.sign(id, null, signaturePositions);
      const msg = signaturePositions.length > 1
        ? `Document signed successfully with ${signaturePositions.length} signatures!`
        : 'Document signed successfully!';
      alert(msg);
      navigate('/documents');
    } catch (err) {
      setError(err.response?.data?.error || 'Failed to sign document');
    } finally {
      setSigning(false);
    }
  };

  // Navigation (don't clear positions - we support multi-page)
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

  if (loading) {
    return <div className="sign-page loading">Loading document...</div>;
  }

  if (error && !signaturePreview) {
    return (
      <div className="sign-page error-page">
        <h2>Cannot Sign Document</h2>
        <p>{error}</p>
        <button onClick={() => navigate('/signature')}>Upload Signature</button>
      </div>
    );
  }

  return (
    <div className="sign-page">
      <div className="sign-header">
        <div className="header-left">
          <button className="btn-back" onClick={() => navigate('/documents')}>
            ← Back
          </button>
          <h1>{document?.filename}</h1>
        </div>
        <div className="header-right">
          {signaturePositions.length > 0 && (
            <span className="sig-count">{signaturePositions.length} signature(s)</span>
          )}
          <button
            className="btn-sign-document"
            onClick={handleSign}
            disabled={signaturePositions.length === 0 || signing}
          >
            {signing ? 'Signing...' : `Sign & Save${signaturePositions.length > 1 ? ` (${signaturePositions.length})` : ''}`}
          </button>
        </div>
      </div>

      <div className="sign-content">
        <div className="pdf-toolbar">
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
                min="80"
                max="300"
                value={currentPagePosition.width}
                onChange={(e) => handleResize(Number(e.target.value))}
              />
              <button className="btn-clear" onClick={handleClearPosition}>
                Remove
              </button>
            </div>
          )}
          {signaturePositions.length > 1 && (
            <div className="toolbar-group">
              <button className="btn-clear-all" onClick={handleClearAllPositions}>
                Clear All ({signaturePositions.length})
              </button>
            </div>
          )}
        </div>

        <div className="pdf-viewer-area">
          <div className="instructions">
            {signaturePositions.length === 0 ? (
              <div className="instructions-content">
                <p>Click anywhere on the document to place your signature, or use auto-detect</p>
                <button
                  className="btn-auto-detect"
                  onClick={handleAutoDetect}
                  disabled={detecting || !signaturePreview}
                >
                  {detecting ? 'Detecting...' : 'Auto-Detect Positions'}
                </button>
              </div>
            ) : (
              <div className="instructions-content">
                <p>
                  {currentPagePosition
                    ? 'Drag to move • Use slider to resize'
                    : 'Click to place signature on this page'}
                  {' • '}{signaturePositions.length} of {numPages} pages have signatures
                </p>
                {detectionInfo && (
                  <span className={`detection-badge ${detectionInfo.confidence}`}>
                    {detectionInfo.total > 1
                      ? `${detectionInfo.total} locations detected`
                      : `${detectionInfo.confidence} confidence`}
                  </span>
                )}
              </div>
            )}
          </div>

          <div
            className={`pdf-page-container ${!currentPagePosition ? 'placing-mode' : ''}`}
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
                  height: isF2F ? 'auto' : currentPagePosition.height * scale,
                }}
                onMouseDown={handleDragStart}
              >
                {isF2F ? (
                  /* F2F Electronic Signature Box Preview */
                  <div className="f2f-signature-box" style={{ transform: `scale(${scale})`, transformOrigin: 'top left' }}>
                    <div className="f2f-header">Electronic Signature</div>
                    <div className="f2f-sig-area">
                      <img src={signaturePreview} alt="Your signature" draggable={false} />
                    </div>
                    <div className="f2f-info">
                      <div className="f2f-row"><span className="f2f-label">Document ID:</span></div>
                      <div className="f2f-row"><span className="f2f-value-blue">xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx</span></div>
                      <div className="f2f-row"><span className="f2f-label">IP Address: ::1</span></div>
                      <div className="f2f-row"><span className="f2f-label">Time: {new Date().toLocaleString('en-US', { weekday: 'long', day: '2-digit', month: 'long', year: 'numeric', hour: '2-digit', minute: '2-digit', second: '2-digit' })}</span></div>
                      <div className="f2f-row"><span className="f2f-label">Signer: </span><span className="f2f-value-blue">{signerName || 'Unknown'}</span></div>
                    </div>
                    <div className="f2f-qr-placeholder"></div>
                  </div>
                ) : (
                  <img src={signaturePreview} alt="Your signature" draggable={false} />
                )}
                <div className="drag-hint">Drag to move</div>
              </div>
            )}
          </div>
        </div>

        {signaturePreview && (
          <div className="signature-preview-panel">
            <h4>Your Signature</h4>
            <img src={signaturePreview} alt="Signature preview" />
          </div>
        )}
      </div>
    </div>
  );
};

export default SignDocument;
