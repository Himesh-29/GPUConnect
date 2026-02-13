import React, { useState, useEffect } from 'react';
import { BrowserRouter as Router, Routes, Route, Link, useNavigate, useLocation } from 'react-router-dom';
import { AuthProvider, useAuth } from './context/AuthContext';
import { Login } from './pages/Login';
import { Register } from './pages/Register';
import { Dashboard } from './pages/Dashboard';
import axios from 'axios';
import './App.css';
import './pages/Auth.css';

const API_URL = import.meta.env.VITE_API_URL || 'http://localhost:8000';

/* ===== Scroll-to-section helper ===== */
const scrollToSection = (id: string) => {
  const el = document.getElementById(id);
  if (el) {
    el.scrollIntoView({ behavior: 'smooth', block: 'start' });
  }
};

/* ===== Navigation ===== */
const Navigation = ({ toggleMenu, isMenuOpen }: any) => {
  const { user, logout } = useAuth();
  const navigate = useNavigate();
  const location = useLocation();

  const handleHashClick = (e: React.MouseEvent, sectionId: string) => {
    e.preventDefault();
    toggleMenu();
    if (location.pathname !== '/') {
      // Navigate home first, then scroll after render
      navigate('/');
      setTimeout(() => scrollToSection(sectionId), 100);
    } else {
      scrollToSection(sectionId);
    }
  };

  return (
    <nav className="navbar">
      <div className="container nav-container">
        <Link to="/" className="logo">
          GPU<span className="logo-accent">Connect</span>
        </Link>

        <button className="mobile-menu-btn" onClick={toggleMenu} aria-label="Toggle Menu">
          <span className="bar" /><span className="bar" /><span className="bar" />
        </button>

        <div className={`nav-links ${isMenuOpen ? 'active' : ''}`}>
          <a href="#marketplace" onClick={(e) => handleHashClick(e, 'marketplace')}>Marketplace</a>
          <a href="#features" onClick={(e) => handleHashClick(e, 'features')}>Features</a>
          <a href="#how-it-works" onClick={(e) => handleHashClick(e, 'how-it-works')}>How It Works</a>
          <a href="#integrate" onClick={(e) => handleHashClick(e, 'integrate')}>Integrate</a>
          <div className="nav-actions">
            {user ? (
              <>
                <Link to="/dashboard" className="btn-secondary btn-sm">Dashboard</Link>
                <button onClick={logout} className="btn-primary btn-sm">Logout</button>
              </>
            ) : (
              <>
                <Link to="/login" className="btn-secondary btn-sm">Sign In</Link>
                <Link to="/register" className="btn-primary btn-sm">Get Started</Link>
              </>
            )}
          </div>
        </div>
      </div>
    </nav>
  );
};


/* ===== Live Models Marketplace ===== */
const Marketplace = () => {
  const [data, setData] = useState<any>(null);

  useEffect(() => {
    const fetchModels = () => {
      axios.get(`${API_URL}/api/computing/models/`).then(r => setData(r.data)).catch(() => {});
    };
    fetchModels();
    const interval = setInterval(fetchModels, 2000);
    return () => clearInterval(interval);
  }, []);

  return (
    <section id="marketplace" className="section-padding bg-dark-alt">
      <div className="container">
        <div className="section-header">
          <div className="badge-gold">Live Network</div>
          <h2 className="section-title">Model <span className="text-gold">Marketplace</span></h2>
          <p className="section-desc">
            Browse models currently available on the network. Powered by real GPU providers.
          </p>
        </div>

        {data && data.models.length > 0 ? (
          <div className="features-grid">
            {data.models.map((m: any) => (
              <div key={m.name} className="feature-card" style={{ display: 'flex', flexDirection: 'column', gap: '12px' }}>
                <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                  <h3 style={{ fontSize: '1.1rem' }}>{m.name}</h3>
                  <span style={{
                    display: 'flex', alignItems: 'center', gap: '6px',
                    fontSize: '12px', color: 'var(--success)'
                  }}>
                    <span style={{ width: 6, height: 6, borderRadius: '50%', background: 'var(--success)', display: 'inline-block' }} />
                    online
                  </span>
                </div>
                <div style={{ display: 'flex', gap: '24px' }}>
                  <div>
                    <div style={{ fontSize: '20px', fontWeight: 700, color: 'var(--accent)' }}>{m.providers}</div>
                    <div style={{ fontSize: '11px', color: 'var(--text-muted)', textTransform: 'uppercase' }}>Provider{m.providers > 1 ? 's' : ''}</div>
                  </div>
                  <div>
                    <div style={{ fontSize: '20px', fontWeight: 700, color: 'var(--text-primary)' }}>$1.00</div>
                    <div style={{ fontSize: '11px', color: 'var(--text-muted)', textTransform: 'uppercase' }}>Per Job</div>
                  </div>
                </div>
                <Link to="/register" className="btn-primary btn-sm" style={{ textAlign: 'center', marginTop: '4px' }}>
                  Use This Model
                </Link>
              </div>
            ))}
          </div>
        ) : (
          <div style={{ textAlign: 'center', padding: '60px 0' }}>
            <p style={{ color: 'var(--text-muted)', fontSize: '16px' }}>
              {data ? 'No GPU nodes are currently online. Be the first provider!' : 'Loading marketplace...'}
            </p>
            <Link to="/register" className="btn-primary" style={{ display: 'inline-block', marginTop: '20px' }}>
              Become a Provider
            </Link>
          </div>
        )}

        <div style={{ textAlign: 'center', marginTop: '40px', color: 'var(--text-muted)', fontSize: '13px' }}>
          <strong style={{ color: 'var(--text-secondary)' }}>{data?.total_nodes || 0}</strong> nodes connected to the network
        </div>
      </div>
    </section>
  );
};


/* ===== Integration Section ===== */
const IntegrateSection = () => (
  <section id="integrate" className="section-padding">
    <div className="container">
      <div className="section-header">
        <div className="badge-gold">For Providers</div>
        <h2 className="section-title">Start <span className="text-gold">Earning</span> in Minutes</h2>
        <p className="section-desc">
          Share your GPU power with the network. No Python required — just run our standalone agent.
        </p>
      </div>

      <div style={{ maxWidth: '700px', margin: '0 auto' }}>
        {/* Step 1 */}
        <div className="feature-card" style={{ marginBottom: '16px' }}>
          <div style={{ display: 'flex', gap: '16px', alignItems: 'flex-start' }}>
            <div style={{
              width: '32px', height: '32px', borderRadius: '50%',
              background: 'var(--accent-dim)', color: 'var(--accent)',
              display: 'flex', alignItems: 'center', justifyContent: 'center',
              fontWeight: 700, fontSize: '14px', flexShrink: 0
            }}>1</div>
            <div>
              <h3 style={{ fontSize: '1rem', marginBottom: '8px' }}>Install Ollama</h3>
              <p style={{ color: 'var(--text-secondary)', fontSize: '14px', marginBottom: '12px' }}>
                One-line install for model management.
              </p>
              <pre style={{
                background: 'rgba(0,0,0,0.4)', padding: '14px 18px',
                borderRadius: '8px', fontSize: '13px', color: 'var(--accent)',
                overflowX: 'auto', border: '1px solid var(--border)'
              }}>
                <code>curl -fsSL https://ollama.com/install.sh | sh</code>
              </pre>
            </div>
          </div>
        </div>

        {/* Step 2 */}
        <div className="feature-card" style={{ marginBottom: '16px' }}>
          <div style={{ display: 'flex', gap: '16px', alignItems: 'flex-start' }}>
            <div style={{
              width: '32px', height: '32px', borderRadius: '50%',
              background: 'var(--accent-dim)', color: 'var(--accent)',
              display: 'flex', alignItems: 'center', justifyContent: 'center',
              fontWeight: 700, fontSize: '14px', flexShrink: 0
            }}>2</div>
            <div>
              <h3 style={{ fontSize: '1rem', marginBottom: '8px' }}>Download the GPU Agent</h3>
              <p style={{ color: 'var(--text-secondary)', fontSize: '14px', marginBottom: '12px' }}>
                Our lightweight agent (10MB) connects your machine to the network automatically.
              </p>
              <div style={{ display: 'flex', gap: '12px', flexWrap: 'wrap' }}>
                <a href="/downloads/gpu-connect.exe" download className="btn-primary btn-sm">
                  Download for Windows (.exe)
                </a>
                <button className="btn-secondary btn-sm" disabled>
                  macOS / Linux (Coming Soon)
                </button>
              </div>
            </div>
          </div>
        </div>

        {/* Step 3 */}
        <div className="feature-card" style={{ marginBottom: '16px' }}>
          <div style={{ display: 'flex', gap: '16px', alignItems: 'flex-start' }}>
            <div style={{
              width: '32px', height: '32px', borderRadius: '50%',
              background: 'var(--accent-dim)', color: 'var(--accent)',
              display: 'flex', alignItems: 'center', justifyContent: 'center',
              fontWeight: 700, fontSize: '14px', flexShrink: 0
            }}>3</div>
            <div>
              <h3 style={{ fontSize: '1rem', marginBottom: '8px' }}>Run & Verify</h3>
              <p style={{ color: 'var(--text-secondary)', fontSize: '14px', marginBottom: '12px' }}>
                Run the executable. It will auto-detect your Ollama models and register your node.
              </p>
              <pre style={{
                background: 'rgba(0,0,0,0.4)', padding: '14px 18px',
                borderRadius: '8px', fontSize: '13px', color: 'var(--accent)',
                overflowX: 'auto', border: '1px solid var(--border)'
              }}>
                <code>.\gpu-connect.exe</code>
              </pre>
            </div>
          </div>
        </div>
      </div>
    </div>
  </section>
);


/* ===== Landing Page ===== */
const LandingPage = () => {
  const [stats, setStats] = useState<any>(null);
  useEffect(() => {
    const fetchStats = () => {
      axios.get(`${API_URL}/api/computing/stats/`).then(r => setStats(r.data)).catch(() => {});
    };
    fetchStats();
    const interval = setInterval(fetchStats, 2000);
    return () => clearInterval(interval);
  }, []);

  return (
    <>
      {/* Hero */}
      <header className="hero-section">
        <div className="container">
          <div className="badge-gold">Open Beta</div>
          <h1 className="hero-title">
            The Future of <br />
            <span className="text-gradient">Distributed AI</span>
          </h1>
          <p className="hero-subtitle">
            Rent GPU power from a decentralized network or monetize your idle hardware.
            No middlemen. No vendor lock-in. Just compute.
          </p>
          <div className="hero-actions">
            <Link to="/register" className="btn-primary-large">Start Computing</Link>
            <a href="#integrate" className="btn-secondary-large">Become a Provider</a>
          </div>

          <div className="glass-card hero-stats">
            <div className="stat-item">
              <span className="stat-value">{stats?.active_nodes ?? '—'}</span>
              <span className="stat-label">Active Nodes</span>
            </div>
            <div className="stat-divider" />
            <div className="stat-item">
              <span className="stat-value">{stats?.available_models ?? '—'}</span>
              <span className="stat-label">Models</span>
            </div>
            <div className="stat-divider" />
            <div className="stat-item">
              <span className="stat-value">{stats?.completed_jobs ?? '—'}</span>
              <span className="stat-label">Jobs Completed</span>
            </div>
            <div className="stat-divider" />
            <div className="stat-item">
              <span className="stat-value">$1.00</span>
              <span className="stat-label">Per Job</span>
            </div>
          </div>
        </div>
      </header>

      {/* Marketplace */}
      <Marketplace />

      {/* Features */}
      <section id="features" className="section-padding">
        <div className="container">
          <div className="section-header">
            <h2 className="section-title">Engineered for <span className="text-gold">Performance</span></h2>
            <p className="section-desc">Enterprise-grade infrastructure with decentralized freedom.</p>
          </div>

          <div className="features-grid">
            <div className="feature-card">
              <div className="icon-box">🔒</div>
              <h3>Sandboxed Execution</h3>
              <p>Every workload runs in isolated containers. Your hardware stays protected, your data stays private.</p>
            </div>
            <div className="feature-card">
              <div className="icon-box">⚡</div>
              <h3>Real-Time WebSockets</h3>
              <p>Low-latency P2P connections dispatch inference tasks to the nearest available node in milliseconds.</p>
            </div>
            <div className="feature-card">
              <div className="icon-box">💰</div>
              <h3>Credit Ledger</h3>
              <p>Transparent credit system with instant settlements. Every compute cycle is tracked and auditable.</p>
            </div>
            <div className="feature-card">
              <div className="icon-box">🌐</div>
              <h3>Multi-Model Support</h3>
              <p>Llama, Gemma, Mistral, Qwen — any model your node supports is automatically available to the network.</p>
            </div>
            <div className="feature-card">
              <div className="icon-box">📊</div>
              <h3>Live Dashboard</h3>
              <p>Monitor your jobs, wallet, and network health in real-time with a modern, responsive dashboard.</p>
            </div>
            <div className="feature-card">
              <div className="icon-box">🔌</div>
              <h3>Zero Config Agents</h3>
              <p>One command installs the agent. It auto-detects your GPU, discovers models, and joins the network.</p>
            </div>
          </div>
        </div>
      </section>

      {/* How It Works */}
      <section id="how-it-works" className="section-padding bg-dark-alt">
        <div className="container">
          <div className="section-header">
            <h2 className="section-title">How It <span className="text-gold">Works</span></h2>
          </div>

          <div className="steps-container">
            <div className="step-card">
              <div className="step-number">01</div>
              <h3>Connect Your GPU</h3>
              <p>Install Ollama, pull a model, run our lightweight agent. Your machine is now a node on the network.</p>
            </div>
            <div className="step-card">
              <div className="step-number">02</div>
              <h3>Accept Jobs</h3>
              <p>The network automatically routes AI inference jobs to your GPU based on model availability and proximity.</p>
            </div>
            <div className="step-card">
              <div className="step-number">03</div>
              <h3>Earn Credits</h3>
              <p>Get paid in Compute Credits for every job completed. Use them for your own inference or cash out.</p>
            </div>
          </div>
        </div>
      </section>

      {/* Integration */}
      <IntegrateSection />

      {/* Footer */}
      <footer className="footer section-padding">
        <div className="container footer-content">
          <div>
            <div className="logo logo-large">GPU<span className="logo-accent">Connect</span></div>
            <p style={{ marginTop: '12px', maxWidth: '300px' }}>The future of AI is distributed. Join the revolution.</p>
          </div>
          <div className="footer-links">
            <div>
              <h4>Platform</h4>
              <a href="#marketplace">Marketplace</a>
              <a href="#features">Features</a>
              <a href="#how-it-works">How It Works</a>
              <a href="#integrate">Integrate</a>
            </div>
            <div>
              <h4>Resources</h4>
              <a href="#">Documentation</a>
              <a href="#">API Reference</a>
              <a href="#">GitHub</a>
            </div>
          </div>
        </div>
        <div className="container copyright">
          © 2026 GPU Connect. All rights reserved.
        </div>
      </footer>
    </>
  );
};


/* ===== App ===== */
function App() {
  const [isMenuOpen, setIsMenuOpen] = useState(false);
  const toggleMenu = () => setIsMenuOpen(!isMenuOpen);

  return (
    <Router>
      <AuthProvider>
        <div className="App">
          <Navigation toggleMenu={toggleMenu} isMenuOpen={isMenuOpen} />
          <Routes>
            <Route path="/" element={<LandingPage />} />
            <Route path="/login" element={<Login />} />
            <Route path="/register" element={<Register />} />
            <Route path="/dashboard" element={<Dashboard />} />
          </Routes>
        </div>
      </AuthProvider>
    </Router>
  );
}

export default App;
