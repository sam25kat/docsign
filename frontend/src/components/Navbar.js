import React from 'react';
import { Link, useNavigate } from 'react-router-dom';
import { useAuth } from '../context/AuthContext';
import './Navbar.css';

const Navbar = () => {
  const { user, logout, isAdmin } = useAuth();
  const navigate = useNavigate();

  const handleLogout = async () => {
    await logout();
    navigate('/login');
  };

  if (!user) return null;

  return (
    <nav className="navbar">
      <div className="navbar-brand">
        <Link to="/">Medical PDF Signer</Link>
      </div>

      <div className="navbar-links">
        <Link to="/documents">Documents</Link>
        <Link to="/signature">My Signature</Link>
        {isAdmin && <Link to="/upload">Upload PDF</Link>}
      </div>

      <div className="navbar-user">
        <span className="user-info">
          {user.name} ({user.role})
        </span>
        <button onClick={handleLogout} className="btn-logout">
          Logout
        </button>
      </div>
    </nav>
  );
};

export default Navbar;
