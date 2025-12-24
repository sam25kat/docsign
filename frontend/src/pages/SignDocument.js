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

  // Signature position state
  const [signaturePosition, setSignaturePosition] = useState(null);
  const [isDragging, setIsDragging] = useState(false);
  const [dragOffset, setDragOffset] = useState({ x: 0, y: 0 });

  const pageContainerRef = useRef(null);
  const signatureRef = useRef(null);

  const loadDocument = useCallback(async () => {
    try {
      const response = await documentAPI.get(id);
      setDocument(response.data.document);

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

  // Place signature on click
  const handlePageClick = (e) => {
    // Don't place new signature if one exists or if clicking on signature overlay
    if (!signaturePreview || signaturePosition) return;
    if (e.target.closest('.signature-overlay')) return;

    const container = pageContainerRef.current;
    if (!container) return;

    const rect = container.getBoundingClientRect();
    const x = (e.clientX - rect.left) / scale;
    const y = (e.clientY - rect.top) / scale;

    setSignaturePosition({
      x: Math.max(0, x - 75), // Center signature on click
      y: Math.max(0, y - 25),
      page: currentPage - 1,
      width: 150,
      height: 50,
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

    // Keep within bounds
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

  // Sign document
  const handleSign = async () => {
    if (!signaturePosition) {
      alert('Please place your signature on the document first.');
      return;
    }

    setSigning(true);
    try {
      await documentAPI.sign(id, signaturePosition);
      alert('Document signed successfully!');
      navigate('/documents');
    } catch (err) {
      setError(err.response?.data?.error || 'Failed to sign document');
    } finally {
      setSigning(false);
    }
  };

  // Navigation
  const goToPrevPage = () => {
    if (currentPage > 1) {
      const newPage = currentPage - 1;
      setCurrentPage(newPage);
      // Clear signature if it's on a different page
      if (signaturePosition && signaturePosition.page !== newPage - 1) {
        setSignaturePosition(null);
      }
    }
  };

  const goToNextPage = () => {
    if (numPages && currentPage < numPages) {
      const newPage = currentPage + 1;
      setCurrentPage(newPage);
      // Clear signature if it's on a different page
      if (signaturePosition && signaturePosition.page !== newPage - 1) {
        setSignaturePosition(null);
      }
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
          <button
            className="btn-sign-document"
            onClick={handleSign}
            disabled={!signaturePosition || signing}
          >
            {signing ? 'Signing...' : 'Sign & Save'}
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

          {signaturePosition && (
            <div className="toolbar-group">
              <label>Size:</label>
              <input
                type="range"
                min="80"
                max="300"
                value={signaturePosition.width}
                onChange={(e) => handleResize(Number(e.target.value))}
              />
              <button className="btn-clear" onClick={handleClearPosition}>
                Remove
              </button>
            </div>
          )}
        </div>

        <div className="pdf-viewer-area">
          <div className="instructions">
            {!signaturePosition ? (
              <p>Click anywhere on the document to place your signature</p>
            ) : (
              <p>Drag to move • Use slider to resize • Click "Sign & Save" when ready</p>
            )}
          </div>

          <div
            className={`pdf-page-container ${!signaturePosition ? 'placing-mode' : ''}`}
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
