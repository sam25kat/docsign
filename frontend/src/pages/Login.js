import React, { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { useAuth } from '../context/AuthContext';
import './Login.css';

const Login = () => {
  const [isRegister, setIsRegister] = useState(false);
  const [formData, setFormData] = useState({
    name: '',
    email: '',
    password: '',
    role: 'doctor',
  });
  const [error, setError] = useState('');
  const [loading, setLoading] = useState(false);
  const { login, register } = useAuth();
  const navigate = useNavigate();

  const handleChange = (e) => {
    setFormData({
      ...formData,
      [e.target.name]: e.target.value,
    });
  };

  const handleSubmit = async (e) => {
    e.preventDefault();
    setError('');
    setLoading(true);

    try {
      if (isRegister) {
        await register(formData.name, formData.email, formData.password, formData.role);
        setIsRegister(false);
        setError('');
        alert('Registration successful! Please login.');
      } else {
        await login(formData.email, formData.password);
        navigate('/documents');
      }
    } catch (err) {
      setError(err.response?.data?.error || 'Something went wrong');
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="login-page">
      <div className="login-container">
        <div className="login-header">
          <h1>Medical PDF Signer</h1>
          <p>Secure document signing for healthcare</p>
        </div>

        <div className="login-card">
          <h2>{isRegister ? 'Create Account' : 'Welcome Back'}</h2>

          <form onSubmit={handleSubmit}>
            {isRegister && (
              <div className="form-group">
                <label htmlFor="name">Full Name</label>
                <input
                  type="text"
                  id="name"
                  name="name"
                  value={formData.name}
                  onChange={handleChange}
                  required={isRegister}
                  placeholder="Dr. John Smith"
                />
              </div>
            )}

            <div className="form-group">
              <label htmlFor="email">Email</label>
              <input
                type="email"
                id="email"
                name="email"
                value={formData.email}
                onChange={handleChange}
                required
                placeholder="doctor@hospital.com"
              />
            </div>

            <div className="form-group">
              <label htmlFor="password">Password</label>
              <input
                type="password"
                id="password"
                name="password"
                value={formData.password}
                onChange={handleChange}
                required
                placeholder="••••••••"
              />
            </div>

            {isRegister && (
              <div className="form-group">
                <label htmlFor="role">Role</label>
                <select
                  id="role"
                  name="role"
                  value={formData.role}
                  onChange={handleChange}
                >
                  <option value="doctor">Doctor</option>
                  <option value="admin">Admin</option>
                </select>
              </div>
            )}

            {error && <div className="form-error">{error}</div>}

            <button type="submit" className="btn-submit" disabled={loading}>
              {loading ? 'Please wait...' : isRegister ? 'Create Account' : 'Login'}
            </button>
          </form>

          <div className="login-footer">
            {isRegister ? (
              <p>
                Already have an account?{' '}
                <button onClick={() => setIsRegister(false)}>Login</button>
              </p>
            ) : (
              <p>
                Don't have an account?{' '}
                <button onClick={() => setIsRegister(true)}>Register</button>
              </p>
            )}
          </div>

          <div className="demo-credentials">
            <p><strong>Demo Admin:</strong> admin@example.com / admin123</p>
          </div>
        </div>
      </div>
    </div>
  );
};

export default Login;
