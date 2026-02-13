import React, { useState, useEffect } from 'react';
import { useAuth } from '../context/AuthContext';
import { LayoutDashboard, Wallet, Server, Activity, RefreshCw } from 'lucide-react';
import JobSubmitter from '../components/JobSubmitter';
import axios from 'axios';
import './Dashboard.css';

const API_URL = import.meta.env.VITE_API_URL || 'http://localhost:8000';

const SidebarItem = ({ icon: Icon, label, active, onClick }: any) => (
  <button className={`sidebar-item ${active ? 'active' : ''}`} onClick={onClick}>
    <Icon size={18} />
    <span>{label}</span>
  </button>
);

const WalletCard = ({ balance, onRefresh }: { balance: number | string, onRefresh: () => void }) => (
  <div className="glass-card wallet-card">
    <div className="wallet-header">
      <span>Total Balance</span>
      <button onClick={onRefresh} className="btn-icon" title="Refresh"><RefreshCw size={14} /></button>
    </div>
    <div className="wallet-balance">${Number(balance).toFixed(2)}</div>
    <div className="wallet-actions">
      <button className="btn-primary-sm">Add Funds</button>
    </div>
  </div>
);

interface JobData {
    id: number; status: string; prompt: string; model: string;
    cost: string | null; result: any; created_at: string; completed_at: string | null;
}

const JobHistory = ({ token }: { token: string | null }) => {
    const [jobs, setJobs] = useState<JobData[]>([]);
    const [loading, setLoading] = useState(true);

    const fetchJobs = async () => {
        setLoading(true);
        try {
            const resp = await axios.get(`${API_URL}/api/computing/jobs/`, {
                headers: { Authorization: `Bearer ${token}` }
            });
            setJobs(resp.data);
        } catch { /* ignore */ }
        setLoading(false);
    };

    useEffect(() => { fetchJobs(); }, []);

    const statusStyle = (s: string) => {
        const colors: Record<string, string> = {
            COMPLETED: 'var(--success)', FAILED: 'var(--error)',
            RUNNING: 'var(--warning)', PENDING: 'var(--text-muted)'
        };
        return colors[s] || 'var(--text-muted)';
    };

    return (
        <div className="glass-card">
            <div className="card-header">
                <h3>Job History</h3>
                <button className="btn-icon" onClick={fetchJobs}><RefreshCw size={14} /></button>
            </div>
            {loading ? <p style={{ color: 'var(--text-muted)' }}>Loading...</p> :
             jobs.length === 0 ? (
                <div className="empty-state">
                    <Activity size={40} className="opacity-50" style={{ color: 'var(--accent)' }} />
                    <p>No jobs submitted yet</p>
                </div>
            ) : (
                <div style={{ display: 'flex', flexDirection: 'column', gap: '8px', maxHeight: '400px', overflowY: 'auto' }}>
                    {jobs.map(j => (
                        <div key={j.id} style={{
                            padding: '12px', borderRadius: '8px',
                            background: 'rgba(255,255,255,0.02)',
                            border: '1px solid var(--border)'
                        }}>
                            <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: '6px' }}>
                                <span style={{ fontSize: '12px', color: 'var(--text-muted)' }}>
                                    #{j.id} · {j.model}
                                </span>
                                <span style={{
                                    fontSize: '11px', fontWeight: 700,
                                    color: statusStyle(j.status),
                                    padding: '2px 8px', borderRadius: '4px',
                                    background: `${statusStyle(j.status)}15`,
                                    letterSpacing: '0.5px'
                                }}>
                                    {j.status}
                                </span>
                            </div>
                            <p style={{ fontSize: '13px', color: 'var(--text-primary)', margin: '4px 0' }}>{j.prompt}</p>
                            {j.result?.output && (
                                <div style={{
                                    fontSize: '12px', color: 'var(--text-secondary)',
                                    background: 'rgba(0,0,0,0.2)', padding: '8px',
                                    borderRadius: '6px', marginTop: '6px',
                                    maxHeight: '80px', overflowY: 'auto', whiteSpace: 'pre-wrap'
                                }}>
                                    {j.result.output}
                                </div>
                            )}
                            {j.result?.error && (
                                <p style={{ fontSize: '12px', color: 'var(--error)', marginTop: '4px' }}>
                                    {j.result.error}
                                </p>
                            )}
                        </div>
                    ))}
                </div>
            )}
        </div>
    );
};

const NodesPanel = () => {
    const [stats, setStats] = useState<any>(null);
    useEffect(() => {
        axios.get(`${API_URL}/api/computing/stats/`).then(r => setStats(r.data)).catch(() => {});
    }, []);

    return (
        <div className="glass-card">
            <div className="card-header">
                <h3>Network</h3>
                <span style={{
                    display: 'flex', alignItems: 'center', gap: '6px',
                    fontSize: '12px', color: stats?.active_nodes > 0 ? 'var(--success)' : 'var(--text-muted)'
                }}>
                    <span style={{
                        width: 6, height: 6, borderRadius: '50%',
                        background: stats?.active_nodes > 0 ? 'var(--success)' : 'var(--text-muted)',
                        display: 'inline-block'
                    }} />
                    {stats?.active_nodes || 0} node{stats?.active_nodes !== 1 ? 's' : ''} online
                </span>
            </div>
            {stats ? (
                <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '16px', marginTop: '8px' }}>
                    <div>
                        <div style={{ fontSize: '24px', fontWeight: 700, color: 'var(--accent)' }}>{stats.active_nodes}</div>
                        <div style={{ fontSize: '12px', color: 'var(--text-muted)' }}>Active Nodes</div>
                    </div>
                    <div>
                        <div style={{ fontSize: '24px', fontWeight: 700, color: 'var(--text-primary)' }}>{stats.available_models}</div>
                        <div style={{ fontSize: '12px', color: 'var(--text-muted)' }}>Models</div>
                    </div>
                    <div>
                        <div style={{ fontSize: '24px', fontWeight: 700, color: 'var(--text-primary)' }}>{stats.total_jobs}</div>
                        <div style={{ fontSize: '12px', color: 'var(--text-muted)' }}>Total Jobs</div>
                    </div>
                    <div>
                        <div style={{ fontSize: '24px', fontWeight: 700, color: 'var(--success)' }}>{stats.completed_jobs}</div>
                        <div style={{ fontSize: '12px', color: 'var(--text-muted)' }}>Completed</div>
                    </div>
                </div>
            ) : (
                <div className="empty-state">
                    <Server size={40} className="opacity-50" style={{ color: 'var(--accent)' }} />
                    <p>Loading network stats...</p>
                </div>
            )}
        </div>
    );
};

export const Dashboard: React.FC = () => {
    const { user, token, logout } = useAuth();
    const [activeTab, setActiveTab] = useState('overview');
    const [balance, setBalance] = useState<number>(0);

    useEffect(() => { if (user) setBalance(Number(user.wallet_balance)); }, [user]);

    const refreshBalance = async () => {
        try {
            const resp = await axios.get(`${API_URL}/api/core/profile/`, {
                headers: { Authorization: `Bearer ${token}` }
            });
            setBalance(Number(resp.data.wallet_balance));
        } catch { /* ignore */ }
    };

    if (!user) return <div style={{ padding: '100px', textAlign: 'center', color: 'var(--text-muted)' }}>Loading...</div>;

    return (
        <div className="dashboard-container">
            <aside className="dashboard-sidebar">
                <div className="sidebar-nav">
                    <SidebarItem icon={LayoutDashboard} label="Overview" active={activeTab === 'overview'} onClick={() => setActiveTab('overview')} />
                    <SidebarItem icon={Wallet} label="Wallet" active={activeTab === 'wallet'} onClick={() => setActiveTab('wallet')} />
                    <SidebarItem icon={Server} label="Network" active={activeTab === 'network'} onClick={() => setActiveTab('network')} />
                </div>
                <div className="sidebar-footer">
                    <div className="user-info">
                        <div className="user-avatar">{user.username[0].toUpperCase()}</div>
                        <div className="user-details">
                            <span className="user-name">{user.username}</span>
                            <span className="user-role">{user.role}</span>
                        </div>
                    </div>
                    <button className="btn-logout" onClick={logout}>Sign Out</button>
                </div>
            </aside>

            <main className="dashboard-content">
                <header className="dashboard-header">
                    <h2>
                        <span style={{ color: 'var(--text-muted)' }}>Dashboard /</span>{' '}
                        <span className="text-gold">{activeTab.charAt(0).toUpperCase() + activeTab.slice(1)}</span>
                    </h2>
                </header>

                <div className="dashboard-grid">
                    <WalletCard balance={balance} onRefresh={refreshBalance} />

                    <div className="glass-card stat-card">
                        <div style={{ fontSize: '13px', color: 'var(--text-muted)', textTransform: 'uppercase', letterSpacing: '0.5px' }}>
                            Credits Used
                        </div>
                        <div className="stat-big">{(100 - balance).toFixed(0)}</div>
                    </div>

                    <div className="glass-card stat-card">
                        <div style={{ fontSize: '13px', color: 'var(--text-muted)', textTransform: 'uppercase', letterSpacing: '0.5px' }}>
                            Cost Per Job
                        </div>
                        <div className="stat-big">$1.00</div>
                        <p style={{ fontSize: '11px', color: 'var(--text-muted)' }}>per inference</p>
                    </div>

                    <div className="grid-full-width">
                        {activeTab === 'overview' && (
                            <div className="overview-grid">
                                <JobSubmitter />
                                <div style={{ display: 'flex', flexDirection: 'column', gap: '20px' }}>
                                    <JobHistory token={token} />
                                    <NodesPanel />
                                </div>
                            </div>
                        )}
                        {activeTab === 'wallet' && (
                            <div className="glass-card">
                                <h3>Wallet Details</h3>
                                <div style={{ display: 'flex', gap: '40px', marginTop: '20px' }}>
                                    <div>
                                        <div style={{ fontSize: '12px', color: 'var(--text-muted)', textTransform: 'uppercase', marginBottom: '4px' }}>Current Balance</div>
                                        <div style={{ fontSize: '2rem', fontWeight: 700, color: 'var(--accent)' }}>${balance.toFixed(2)}</div>
                                    </div>
                                    <div>
                                        <div style={{ fontSize: '12px', color: 'var(--text-muted)', textTransform: 'uppercase', marginBottom: '4px' }}>Starting Balance</div>
                                        <div style={{ fontSize: '2rem', fontWeight: 700, color: 'var(--text-primary)' }}>$100.00</div>
                                    </div>
                                </div>
                                <p style={{ color: 'var(--text-muted)', fontSize: '13px', marginTop: '16px' }}>
                                    Each inference job costs 1.00 credit. Credits are deducted on submission.
                                </p>
                            </div>
                        )}
                        {activeTab === 'network' && <NodesPanel />}
                    </div>
                </div>
            </main>
        </div>
    );
};
