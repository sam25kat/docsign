import React from 'react';
import { BrowserRouter as Router, Routes, Route, Navigate } from 'react-router-dom';
import { AuthProvider, useAuth } from './context/AuthContext';
import Navbar from './components/Navbar';
import Login from './pages/Login';
import Documents from './pages/Documents';
import SignDocument from './pages/SignDocument';
import ViewDocument from './pages/ViewDocument';
import UploadDocument from './pages/UploadDocument';
import Signature from './pages/Signature';
import './App.css';

// Protected Route Component
const ProtectedRoute = ({ children, adminOnly = false }) => {
  const { user, loading, isAdmin } = useAuth();

  if (loading) {
    return <div className="loading-screen">Loading...</div>;
  }

  if (!user) {
    return <Navigate to="/login" />;
  }

  if (adminOnly && !isAdmin) {
    return <Navigate to="/documents" />;
  }

  return children;
};

// Public Route (redirect to documents if logged in)
const PublicRoute = ({ children }) => {
  const { user, loading } = useAuth();

  if (loading) {
    return <div className="loading-screen">Loading...</div>;
  }

  if (user) {
    return <Navigate to="/documents" />;
  }

  return children;
};

// Main Layout with Navbar
const Layout = ({ children }) => {
  return (
    <div className="app-layout">
      <Navbar />
      <main className="main-content">{children}</main>
    </div>
  );
};

function AppRoutes() {
  return (
    <Routes>
      {/* Public Routes */}
      <Route
        path="/login"
        element={
          <PublicRoute>
            <Login />
          </PublicRoute>
        }
      />

      {/* Protected Routes */}
      <Route
        path="/"
        element={
          <ProtectedRoute>
            <Navigate to="/documents" />
          </ProtectedRoute>
        }
      />

      <Route
        path="/documents"
        element={
          <ProtectedRoute>
            <Layout>
              <Documents />
            </Layout>
          </ProtectedRoute>
        }
      />

      <Route
        path="/sign/:id"
        element={
          <ProtectedRoute>
            <Layout>
              <SignDocument />
            </Layout>
          </ProtectedRoute>
        }
      />

      <Route
        path="/view/:id"
        element={
          <ProtectedRoute>
            <Layout>
              <ViewDocument />
            </Layout>
          </ProtectedRoute>
        }
      />

      <Route
        path="/signature"
        element={
          <ProtectedRoute>
            <Layout>
              <Signature />
            </Layout>
          </ProtectedRoute>
        }
      />

      <Route
        path="/upload"
        element={
          <ProtectedRoute adminOnly>
            <Layout>
              <UploadDocument />
            </Layout>
          </ProtectedRoute>
        }
      />

      {/* Catch all */}
      <Route path="*" element={<Navigate to="/" />} />
    </Routes>
  );
}

function App() {
  return (
    <Router>
      <AuthProvider>
        <AppRoutes />
      </AuthProvider>
    </Router>
  );
}

export default App;
