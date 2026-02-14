import React, { useEffect, useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { useAuth } from '../context/AuthContext';

/**
 * OAuth Callback Page
 * 
 * Flow:
 * 1. User completes OAuth with Google/GitHub/Microsoft
 * 2. allauth redirects to backend /api/auth/oauth/callback/complete/
 * 3. Backend generates JWT tokens and redirects here with tokens in URL hash
 * 4. This page reads tokens from the hash fragment and stores them
 * 5. No cross-site cookies needed — works in all browsers
 */
export const OAuthCallback: React.FC = () => {
  const [status, setStatus] = useState('Completing sign in...');
  const navigate = useNavigate();
  const { login } = useAuth();

  useEffect(() => {
    const processOAuthTokens = () => {
      try {
        // Read tokens from URL hash fragment
        // URL looks like: /oauth/callback#access=xxx&refresh=xxx&user=xxx
        const hash = window.location.hash.substring(1); // Remove the '#'
        
        if (!hash) {
          setStatus('Authentication failed. No credentials received.');
          setTimeout(() => navigate('/login'), 2000);
          return;
        }

        const params = new URLSearchParams(hash);
        const accessToken = params.get('access');
        const userDataStr = params.get('user');

        if (accessToken) {
          login(accessToken);
          setStatus('Success! Redirecting...');
          
          // Clean the URL hash so tokens aren't visible in browser history
          window.history.replaceState(null, '', '/oauth/callback');
          
          setTimeout(() => navigate('/dashboard'), 500);
        } else {
          setStatus('Authentication failed. Please try again.');
          setTimeout(() => navigate('/login'), 2000);
        }
      } catch (err: any) {
        console.error('OAuth callback error:', err);
        setStatus('Authentication failed. Please try again.');
        setTimeout(() => navigate('/login'), 2000);
      }
    };

    processOAuthTokens();
  }, []);

  return (
    <div style={{
      minHeight: '100vh',
      display: 'flex',
      alignItems: 'center',
      justifyContent: 'center',
      background: 'var(--bg-primary)',
      flexDirection: 'column',
      gap: '16px'
    }}>
      <div style={{
        width: 40, height: 40,
        border: '3px solid var(--border)',
        borderTopColor: 'var(--accent)',
        borderRadius: '50%',
        animation: 'spin 0.8s linear infinite'
      }} />
      <p style={{
        color: 'var(--text-secondary)',
        fontSize: '15px',
        fontFamily: 'var(--font-body)'
      }}>
        {status}
      </p>
    </div>
  );
};
