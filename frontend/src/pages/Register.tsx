import React, { useState } from 'react';
import { useNavigate, Link } from 'react-router-dom';
import { useAuth } from '../context/AuthContext';
import axios from 'axios';
import './Auth.css';

const API_URL = import.meta.env.VITE_API_URL || 'http://localhost:8000';

export const Register: React.FC = () => {
  const [username, setUsername] = useState('');
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [role, setRole] = useState('USER');
  const [error, setError] = useState('');
  const navigate = useNavigate();
  const { login } = useAuth();

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setError('');
    try {
      await axios.post(`${API_URL}/api/core/register/`, {
        username, email, password, role
      });
      // Auto-login after registration
      const response = await axios.post(`${API_URL}/api/core/token/`, {
        username, password
      });
      login(response.data.access);
      navigate('/dashboard');
    } catch (err: any) {
      const data = err.response?.data;
      if (data) {
        // Build human-readable error from serializer errors
        const messages = Object.values(data).flat().join(' ');
        setError(messages || 'Registration failed.');
      } else {
        setError('Registration failed. Please try again.');
      }
    }
  };

  return (
    <div className="auth-page">
      <div className="auth-card">
        <h2>Create Account</h2>
        <p className="auth-subtitle">Join the decentralized GPU network</p>
        {error && <div className="auth-error">{error}</div>}
        <form className="auth-form" onSubmit={handleSubmit}>
          <input
            type="text"
            placeholder="Username"
            value={username}
            onChange={(e) => setUsername(e.target.value)}
            required
          />
          <input
            type="email"
            placeholder="Email"
            value={email}
            onChange={(e) => setEmail(e.target.value)}
            required
          />
          <input
            type="password"
            placeholder="Password (min 8 characters)"
            value={password}
            onChange={(e) => setPassword(e.target.value)}
            required
            minLength={8}
          />
          <select
            value={role}
            onChange={(e) => setRole(e.target.value)}
            style={{
              padding: '12px 16px',
              borderRadius: 'var(--radius-sm, 8px)',
              background: 'rgba(255,255,255,0.04)',
              border: '1px solid rgba(255,255,255,0.06)',
              color: '#f0f0f5',
              fontSize: '14px',
              fontFamily: 'inherit'
            }}
          >
            <option value="USER">🖥 Consumer — Rent GPU Power</option>
            <option value="PROVIDER">⚡ Provider — Share Your GPU</option>
          </select>
          <button type="submit" className="btn-primary">Create Account</button>
        </form>
        <div className="auth-footer">
          Already have an account? <Link to="/login">Sign in</Link>
        </div>
      </div>
    </div>
  );
};
