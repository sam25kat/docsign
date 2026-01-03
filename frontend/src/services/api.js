import axios from 'axios';

const API_URL = process.env.REACT_APP_API_URL || 'http://localhost:5000/api';

const api = axios.create({
  baseURL: API_URL,
  withCredentials: true,
  headers: {
    'Content-Type': 'application/json',
  },
});

// Auth APIs
export const authAPI = {
  register: (data) => api.post('/auth/register', data),
  login: (data) => api.post('/auth/login', data),
  logout: () => api.post('/auth/logout'),
  me: () => api.get('/auth/me'),
};

// Signature APIs
export const signatureAPI = {
  upload: (formData) => api.post('/signatures/upload', formData, {
    headers: { 'Content-Type': 'multipart/form-data' },
  }),
  preview: () => api.get('/signatures/preview'),
  delete: () => api.delete('/signatures/delete'),
};

// Document APIs
export const documentAPI = {
  upload: (formData) => api.post('/documents/upload', formData, {
    headers: { 'Content-Type': 'multipart/form-data' },
  }),
  list: (status = 'pending') => api.get(`/documents?status=${status}`),
  get: (id) => api.get(`/documents/${id}`),
  getFile: (id) => api.get(`/documents/${id}/file`, { responseType: 'blob' }),
  getFileUrl: (id) => `${API_URL}/documents/${id}/file`,
  sign: (id, position, positions) => api.post(`/documents/${id}/sign`, {
    position,   // Single position (backward compat)
    positions   // Multiple positions array
  }),
  download: (id) => `${API_URL}/documents/${id}/download`,
  downloadBlob: (id) => api.get(`/documents/${id}/download`, { responseType: 'blob' }),
  delete: (id) => api.delete(`/documents/${id}/delete`),

  // Auto-detect and bulk signing
  detectSignaturePosition: (id) => api.get(`/documents/${id}/detect-signature-position`),
  bulkDetect: (documentIds) => api.post('/documents/bulk-detect', { document_ids: documentIds }),
  bulkSign: (documents, autoMode = false) => api.post('/documents/bulk-sign', {
    documents,
    auto_mode: autoMode,
  }),
};

export default api;
