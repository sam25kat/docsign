import React, { useState, useEffect, useCallback } from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import { Document, Page, pdfjs } from 'react-pdf';
import { documentAPI } from '../services/api';
import 'react-pdf/dist/esm/Page/AnnotationLayer.css';
import 'react-pdf/dist/esm/Page/TextLayer.css';
import './ViewDocument.css';

pdfjs.GlobalWorkerOptions.workerSrc = `//cdnjs.cloudflare.com/ajax/libs/pdf.js/${pdfjs.version}/pdf.worker.min.js`;

const ViewDocument = () => {
  const { id } = useParams();
  const navigate = useNavigate();

  const [document, setDocument] = useState(null);
  const [pdfUrl, setPdfUrl] = useState(null);
  const [numPages, setNumPages] = useState(null);
  const [currentPage, setCurrentPage] = useState(1);
  const [scale, setScale] = useState(1.0);
  const [loading, setLoading] = useState(true);

  const loadDocument = useCallback(async () => {
    try {
      const response = await documentAPI.get(id);
      setDocument(response.data.document);

      // Fetch signed PDF as blob with credentials
      const fileResponse = await documentAPI.downloadBlob(id);
      const blobUrl = URL.createObjectURL(fileResponse.data);
      setPdfUrl(blobUrl);
    } catch (err) {
      console.error(err);
    } finally {
      setLoading(false);
    }
  }, [id]);

  useEffect(() => {
    loadDocument();
  }, [loadDocument]);

  // Cleanup blob URL on unmount
  useEffect(() => {
    return () => {
      if (pdfUrl && pdfUrl.startsWith('blob:')) {
        URL.revokeObjectURL(pdfUrl);
      }
    };
  }, [pdfUrl]);

  const onDocumentLoadSuccess = ({ numPages: totalPages }) => {
    setNumPages(totalPages);
  };

  const handleDownload = async () => {
    try {
      const response = await documentAPI.downloadBlob(id);
      const url = URL.createObjectURL(response.data);
      const a = window.document.createElement('a');
      a.href = url;
      a.download = `signed_${document?.filename || 'document.pdf'}`;
      window.document.body.appendChild(a);
      a.click();
      window.document.body.removeChild(a);
      URL.revokeObjectURL(url);
    } catch (err) {
      console.error('Download failed:', err);
    }
  };

  if (loading) {
    return <div className="view-page loading">Loading document...</div>;
  }

  return (
    <div className="view-page">
      <div className="view-header">
        <div className="header-left">
          <button className="btn-back" onClick={() => navigate('/documents')}>
            ← Back to Documents
          </button>
          <div className="doc-info">
            <h1>{document?.filename}</h1>
            <div className="doc-meta">
              <span className="badge badge-signed">Signed</span>
              <span>by {document?.signed_by}</span>
              <span>•</span>
              <span>{new Date(document?.signed_at).toLocaleDateString()}</span>
            </div>
          </div>
        </div>
        <div className="header-right">
          <button className="btn-download" onClick={handleDownload}>
            ⬇ Download Signed PDF
          </button>
        </div>
      </div>

      <div className="view-content">
        <div className="pdf-toolbar">
          <div className="toolbar-group">
            <button onClick={() => setCurrentPage(p => Math.max(1, p - 1))} disabled={currentPage <= 1}>
              ← Prev
            </button>
            <span>Page {currentPage} / {numPages || '...'}</span>
            <button onClick={() => setCurrentPage(p => Math.min(numPages, p + 1))} disabled={currentPage >= numPages}>
              Next →
            </button>
          </div>

          <div className="toolbar-group">
            <button onClick={() => setScale(s => Math.max(0.5, s - 0.1))}>−</button>
            <span>{Math.round(scale * 100)}%</span>
            <button onClick={() => setScale(s => Math.min(2, s + 0.1))}>+</button>
          </div>
        </div>

        <div className="pdf-viewer-area">
          <div className="pdf-container">
            <Document
              file={pdfUrl}
              onLoadSuccess={onDocumentLoadSuccess}
            >
              <Page pageNumber={currentPage} scale={scale} />
            </Document>
          </div>
        </div>
      </div>
    </div>
  );
};

export default ViewDocument;
