import React, { useState, useRef, useEffect } from 'react';
import { Document, Page, pdfjs } from 'react-pdf';
import 'react-pdf/dist/esm/Page/AnnotationLayer.css';
import 'react-pdf/dist/esm/Page/TextLayer.css';
import './PDFViewer.css';

// Set up PDF.js worker
pdfjs.GlobalWorkerOptions.workerSrc = `//cdnjs.cloudflare.com/ajax/libs/pdf.js/${pdfjs.version}/pdf.worker.min.js`;

const PDFViewer = ({
  fileUrl,
  signaturePreview,
  onPositionSelect,
  selectedPosition,
  mode = 'view', // 'view' | 'sign'
}) => {
  const [numPages, setNumPages] = useState(null);
  const [currentPage, setCurrentPage] = useState(1);
  const [scale, setScale] = useState(1.0);
  const [isPlacingSignature, setIsPlacingSignature] = useState(false);
  const containerRef = useRef(null);
  const pageRef = useRef(null);

  const onDocumentLoadSuccess = ({ numPages }) => {
    setNumPages(numPages);
  };

  const handlePageClick = (e) => {
    if (mode !== 'sign' || !isPlacingSignature) return;

    const rect = pageRef.current.getBoundingClientRect();
    const x = (e.clientX - rect.left) / scale;
    const y = (e.clientY - rect.top) / scale;

    onPositionSelect({
      x: Math.round(x),
      y: Math.round(y),
      page: currentPage - 1,
      width: 150,
      height: 50,
    });
    setIsPlacingSignature(false);
  };

  const goToPrevPage = () => {
    setCurrentPage((prev) => Math.max(1, prev - 1));
  };

  const goToNextPage = () => {
    setCurrentPage((prev) => Math.min(numPages || 1, prev + 1));
  };

  const zoomIn = () => setScale((prev) => Math.min(2, prev + 0.1));
  const zoomOut = () => setScale((prev) => Math.max(0.5, prev - 0.1));

  return (
    <div className="pdf-viewer-container">
      <div className="pdf-toolbar">
        <div className="toolbar-section">
          <button onClick={goToPrevPage} disabled={currentPage <= 1}>
            ← Prev
          </button>
          <span className="page-info">
            Page {currentPage} of {numPages || '...'}
          </span>
          <button onClick={goToNextPage} disabled={currentPage >= numPages}>
            Next →
          </button>
        </div>

        <div className="toolbar-section">
          <button onClick={zoomOut}>−</button>
          <span className="zoom-info">{Math.round(scale * 100)}%</span>
          <button onClick={zoomIn}>+</button>
        </div>

        {mode === 'sign' && (
          <div className="toolbar-section">
            <button
              className={`btn-place-signature ${isPlacingSignature ? 'active' : ''}`}
              onClick={() => setIsPlacingSignature(!isPlacingSignature)}
            >
              {isPlacingSignature ? 'Click on PDF to place' : 'Place Signature'}
            </button>
          </div>
        )}
      </div>

      <div
        className={`pdf-container ${isPlacingSignature ? 'placing-mode' : ''}`}
        ref={containerRef}
      >
        <div
          className="pdf-page-wrapper"
          ref={pageRef}
          onClick={handlePageClick}
          style={{ position: 'relative' }}
        >
          <Document file={fileUrl} onLoadSuccess={onDocumentLoadSuccess}>
            <Page
              pageNumber={currentPage}
              scale={scale}
              renderTextLayer={true}
              renderAnnotationLayer={true}
            />
          </Document>

          {selectedPosition && selectedPosition.page === currentPage - 1 && (
            <div
              className="signature-preview-overlay"
              style={{
                left: selectedPosition.x * scale,
                top: selectedPosition.y * scale,
                width: selectedPosition.width * scale,
                height: selectedPosition.height * scale,
              }}
            >
              {signaturePreview ? (
                <img src={signaturePreview} alt="Signature" />
              ) : (
                <span>Signature</span>
              )}
            </div>
          )}
        </div>
      </div>

      {isPlacingSignature && (
        <div className="placement-hint">
          Click anywhere on the document to place your signature
        </div>
      )}
    </div>
  );
};

export default PDFViewer;
