import React, { useState, useEffect, useCallback } from 'react';
import { useAuth } from '../context/AuthContext';
import { useDashboard } from '../context/DashboardContext';
import { LayoutDashboard, Wallet, Server, Activity, RefreshCw, TrendingUp, Cpu, ArrowUpRight, ArrowDownRight, Filter } from 'lucide-react';
import { AreaChart, Area, BarChart, Bar, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer, PieChart, Pie, Cell } from 'recharts';
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

/* ===== Stat Card (Small) ===== */
const StatCard = ({ label, value, sub, color, icon: Icon }: any) => (
  <div className="glass-card stat-card">
    <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start' }}>
      <div>
        <div style={{ fontSize: '12px', color: 'var(--text-muted)', textTransform: 'uppercase', letterSpacing: '0.5px', marginBottom: '8px' }}>
          {label}
        </div>
        <div className="stat-big" style={{ color: color || 'var(--text-primary)' }}>{value}</div>
        {sub && <p style={{ fontSize: '11px', color: 'var(--text-muted)', marginTop: '2px' }}>{sub}</p>}
      </div>
      {Icon && <Icon size={20} style={{ color: color || 'var(--accent)', opacity: 0.6 }} />}
    </div>
  </div>
);

/* ===== Wallet Card ===== */
const WalletCard = ({ balance, onRefresh }: { balance: number, onRefresh: () => void }) => (
  <div className="glass-card wallet-card">
    <div className="wallet-header">
      <span>Total Balance</span>
      <button onClick={onRefresh} className="btn-icon" title="Refresh"><RefreshCw size={14} /></button>
    </div>
    <div className="wallet-balance">${balance.toFixed(2)}</div>
    <div className="wallet-actions">
      <button className="btn-primary-sm">Add Funds</button>
    </div>
  </div>
);

/* ===== Job History ===== */
const JobHistory = () => {
  const { recentJobs } = useDashboard();
  const [statusFilter, setStatusFilter] = useState<string>('ALL');

  // Using streaming jobs from context
  const jobs = recentJobs;

  const statusStyle = (s: string) => {
    const colors: Record<string, string> = {
      COMPLETED: 'var(--success)', FAILED: 'var(--error)',
      RUNNING: 'var(--warning)', PENDING: 'var(--text-muted)'
    };
    return colors[s] || 'var(--text-muted)';
  };

  const filtered = statusFilter === 'ALL' ? jobs : jobs.filter(j => j.status === statusFilter);

  return (
    <div className="glass-card">
      <div className="card-header">
        <h3>Job History</h3>
        <div style={{ display: 'flex', gap: '8px', alignItems: 'center' }}>
          <select
            value={statusFilter}
            onChange={e => setStatusFilter(e.target.value)}
            style={{
              background: 'rgba(255,255,255,0.05)', border: '1px solid var(--border)',
              color: 'var(--text-primary)', borderRadius: '6px', padding: '4px 8px', fontSize: '11px'
            }}
          >
            <option value="ALL">All</option>
            <option value="COMPLETED">Completed</option>
            <option value="RUNNING">Running</option>
            <option value="PENDING">Pending</option>
            <option value="FAILED">Failed</option>
          </select>
        </div>
      </div>
      {jobs.length === 0 ? (
          <div className="empty-state">
            <Activity size={40} className="opacity-50" style={{ color: 'var(--accent)' }} />
            <p>No jobs {statusFilter !== 'ALL' ? `with status ${statusFilter}` : 'submitted yet'}</p>
          </div>
        ) : (
          <div style={{ display: 'flex', flexDirection: 'column', gap: '8px', maxHeight: '400px', overflowY: 'auto' }}>
            {filtered.map(j => (
              <div key={j.id} style={{
                padding: '12px', borderRadius: '8px',
                background: 'rgba(255,255,255,0.02)', border: '1px solid var(--border)'
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

/* ===== Nodes Panel ===== */
const NodesPanel = () => {
  const { stats } = useDashboard();
  
  // Stats are streaming now!

  return (
    <div className="glass-card">
      <div className="card-header">
        <h3>Network</h3>
        <span style={{
          display: 'flex', alignItems: 'center', gap: '6px',
          fontSize: '12px', color: (stats?.active_nodes || 0) > 0 ? 'var(--success)' : 'var(--text-muted)'
        }}>
          <span style={{
            width: 6, height: 6, borderRadius: '50%',
            background: (stats?.active_nodes || 0) > 0 ? 'var(--success)' : 'var(--text-muted)',
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

/* ===== Live Models ===== */
const LiveModels = () => {
  const { models } = useDashboard();

  return (
    <div className="glass-card" style={{ gridColumn: '1 / -1' }}>
      <div className="card-header">
        <h3>Live Models</h3>
        <span style={{ fontSize: '12px', color: 'var(--success)', display: 'flex', alignItems: 'center', gap: '6px' }}>
          <span style={{ width: 6, height: 6, borderRadius: '50%', background: 'var(--success)' }} />
          Real-time
        </span>
      </div>
      {models.length > 0 ? (
        <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fill, minmax(200px, 1fr))', gap: '12px' }}>
          {models.map((m) => (
            <div key={m.name} style={{
              padding: '12px', borderRadius: '8px',
              background: 'rgba(255,255,255,0.03)', border: '1px solid var(--border)'
            }}>
              <div style={{ fontWeight: 600, fontSize: '14px', marginBottom: '4px', color: 'var(--text-primary)' }}>{m.name}</div>
              <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                <span style={{ fontSize: '12px', color: 'var(--accent)' }}>{m.providers} Provider{m.providers > 1 ? 's' : ''}</span>
                <span style={{ fontSize: '12px', color: 'var(--text-muted)' }}>$1.00/job</span>
              </div>
            </div>
          ))}
        </div>
      ) : (
        <div className="empty-state">
          <p>No models currently online.</p>
        </div>
      )}
    </div>
  );
};


/* ===== AGENT TOKEN MANAGER ===== */
const AgentTokenManager = ({ token }: { token: string | null }) => {
  const [tokens, setTokens] = useState<any[]>([]);
  const [newToken, setNewToken] = useState<string | null>(null);
  const [label, setLabel] = useState('');
  const [generating, setGenerating] = useState(false);
  const [copied, setCopied] = useState(false);

  const fetchTokens = async () => {
    try {
      const resp = await axios.get(`${API_URL}/api/core/agent-token/list/`, {
        headers: { Authorization: `Bearer ${token}` }
      });
      setTokens(resp.data);
    } catch { /* ignore */ }
  };

  useEffect(() => { fetchTokens(); }, []);

  const generateToken = async () => {
    setGenerating(true);
    try {
      const resp = await axios.post(`${API_URL}/api/core/agent-token/generate/`, {
        label: label || 'Default Agent'
      }, {
        headers: { Authorization: `Bearer ${token}` }
      });
      setNewToken(resp.data.token);
      setLabel('');
      fetchTokens();
    } catch (err: any) {
      alert(err.response?.data?.error || 'Failed to generate token');
    }
    setGenerating(false);
  };

  const revokeToken = async (id: number) => {
    if (!confirm('Revoke this token? Any agent using it will be disconnected.')) return;
    try {
      await axios.post(`${API_URL}/api/core/agent-token/${id}/revoke/`, {}, {
        headers: { Authorization: `Bearer ${token}` }
      });
      fetchTokens();
    } catch { /* ignore */ }
  };

  const copyToken = () => {
    if (newToken) {
      navigator.clipboard.writeText(newToken);
      setCopied(true);
      setTimeout(() => setCopied(false), 2000);
    }
  };

  return (
    <div className="glass-card">
      <div className="card-header">
        <h3>🔑 Agent Tokens</h3>
        <span style={{ fontSize: '12px', color: 'var(--text-muted)' }}>Secure authentication for GPU agents</span>
      </div>

      {/* Generate Token */}
      <div style={{
        display: 'flex', gap: '8px', marginBottom: '16px', alignItems: 'center'
      }}>
        <input
          type="text"
          placeholder="Token label (e.g. 'Home PC')"
          value={label}
          onChange={e => setLabel(e.target.value)}
          style={{
            flex: 1, padding: '8px 12px', borderRadius: '6px', fontSize: '13px',
            background: 'rgba(255,255,255,0.04)', border: '1px solid var(--border)',
            color: 'var(--text-primary)', fontFamily: 'var(--font-body)'
          }}
        />
        <button
          className="btn-primary-sm"
          onClick={generateToken}
          disabled={generating}
          style={{ whiteSpace: 'nowrap' }}
        >
          {generating ? 'Generating...' : '+ Generate Token'}
        </button>
      </div>

      {/* Show new token (once) */}
      {newToken && (
        <div style={{
          padding: '16px', borderRadius: '10px', marginBottom: '16px',
          background: 'rgba(34,197,94,0.08)', border: '1px solid rgba(34,197,94,0.25)'
        }}>
          <div style={{ fontSize: '12px', color: 'var(--success)', fontWeight: 700, marginBottom: '8px' }}>
            ⚠️ SAVE THIS TOKEN — It will NOT be shown again!
          </div>
          <div style={{
            display: 'flex', alignItems: 'center', gap: '8px',
            background: 'rgba(0,0,0,0.3)', padding: '10px 14px', borderRadius: '8px',
            fontFamily: 'monospace', fontSize: '13px', color: 'var(--text-primary)',
            wordBreak: 'break-all'
          }}>
            <span style={{ flex: 1 }}>{newToken}</span>
            <button
              onClick={copyToken}
              style={{
                padding: '4px 12px', borderRadius: '4px', fontSize: '11px', fontWeight: 700,
                background: copied ? 'rgba(34,197,94,0.2)' : 'rgba(255,255,255,0.1)',
                color: copied ? 'var(--success)' : 'var(--text-primary)',
                border: 'none', cursor: 'pointer', whiteSpace: 'nowrap'
              }}
            >
              {copied ? '✓ Copied!' : 'Copy'}
            </button>
          </div>
          <div style={{ fontSize: '11px', color: 'var(--text-muted)', marginTop: '8px' }}>
            Run the agent and paste this token when prompted.
          </div>
        </div>
      )}

      {/* Active tokens list */}
      {tokens.length > 0 ? (
        <div style={{ display: 'flex', flexDirection: 'column', gap: '8px' }}>
          {tokens.map(t => (
            <div key={t.id} style={{
              display: 'flex', justifyContent: 'space-between', alignItems: 'center',
              padding: '10px 14px', borderRadius: '8px',
              background: 'rgba(255,255,255,0.02)', border: '1px solid var(--border)'
            }}>
              <div style={{ display: 'flex', alignItems: 'center', gap: '10px' }}>
                <span style={{ fontSize: '16px' }}>🔑</span>
                <div>
                  <div style={{ fontSize: '13px', fontWeight: 600, color: 'var(--text-primary)' }}>{t.label}</div>
                  <div style={{ fontSize: '11px', color: 'var(--text-muted)' }}>
                    {t.token_prefix} · Created {new Date(t.created_at).toLocaleDateString()}
                    {t.last_used && ` · Last used ${new Date(t.last_used).toLocaleString()}`}
                  </div>
                </div>
              </div>
              <button
                onClick={() => revokeToken(t.id)}
                style={{
                  padding: '4px 12px', borderRadius: '4px', fontSize: '11px', fontWeight: 700,
                  background: 'rgba(239,68,68,0.1)', color: 'var(--error)',
                  border: '1px solid rgba(239,68,68,0.2)', cursor: 'pointer'
                }}
              >
                Revoke
              </button>
            </div>
          ))}
        </div>
      ) : (
        <p style={{ fontSize: '13px', color: 'var(--text-muted)', textAlign: 'center', padding: '10px' }}>
          No active tokens. Generate one to connect your GPU agent.
        </p>
      )}
    </div>
  );
};

/* ===== PROVIDER DASHBOARD TAB ===== */
const CHART_COLORS = ['#d4a037', '#f0c95c', '#b8860b', '#ffd700', '#e6b800', '#cc9900'];

const ProviderDashboard = ({ token }: { token: string | null }) => {
  const [data, setData] = useState<any>(null);
  const [days, setDays] = useState(30);
  const [txFilter, setTxFilter] = useState<string>('all');
  const [loading, setLoading] = useState(true);

  const fetchStats = useCallback(async (silent = false) => {
    if (!silent) setLoading(true);
    try {
      const resp = await axios.get(`${API_URL}/api/computing/provider-stats/?days=${days}`, {
        headers: { Authorization: `Bearer ${token}` }
      });
      setData(resp.data);
    } catch { /* ignore */ }
    setLoading(false);
  }, [days, token]);

  useEffect(() => {
    fetchStats();
    const interval = setInterval(() => fetchStats(true), 3000);
    return () => clearInterval(interval);
  }, [fetchStats]);

  if (loading && !data) {
    return <div className="glass-card"><p style={{ color: 'var(--text-muted)', padding: '40px', textAlign: 'center' }}>Loading provider stats...</p></div>;
  }
  if (!data) return null;

  const { provider, consumer, wallet_balance, transactions } = data;
  const filteredTx = txFilter === 'all' ? transactions : transactions.filter((t: any) => t.type === txFilter);

  // Custom tooltip for charts
  const ChartTooltip = ({ active, payload, label }: any) => {
    if (!active || !payload?.length) return null;
    return (
      <div style={{
        background: 'var(--bg-card)', border: '1px solid var(--border)',
        borderRadius: '8px', padding: '10px 14px', boxShadow: '0 8px 32px rgba(0,0,0,0.4)'
      }}>
        <div style={{ fontSize: '12px', color: 'var(--text-muted)', marginBottom: '4px' }}>{label}</div>
        {payload.map((p: any, i: number) => (
          <div key={i} style={{ fontSize: '13px', fontWeight: 600, color: p.color }}>
            {p.name}: {typeof p.value === 'number' ? (p.name.includes('$') || p.name.includes('Earned') ? `$${p.value.toFixed(2)}` : p.value) : p.value}
          </div>
        ))}
      </div>
    );
  };

  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: '20px' }}>
      {/* --- Agent Token Management --- */}
      <AgentTokenManager token={token} />

      {/* --- Period Filter --- */}
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
        <h3 style={{ margin: 0, color: 'var(--text-primary)' }}>Provider Analytics</h3>
        <div style={{ display: 'flex', gap: '6px' }}>
          {[7, 14, 30, 90].map(d => (
            <button
              key={d}
              onClick={() => setDays(d)}
              style={{
                padding: '5px 12px', borderRadius: '6px', fontSize: '12px', fontWeight: 600, cursor: 'pointer',
                border: days === d ? '1px solid var(--accent)' : '1px solid var(--border)',
                background: days === d ? 'rgba(212,160,55,0.15)' : 'rgba(255,255,255,0.03)',
                color: days === d ? 'var(--accent)' : 'var(--text-muted)',
                transition: 'all 0.2s',
              }}
            >
              {d}d
            </button>
          ))}
        </div>
      </div>

      {/* --- Top KPI Cards --- */}
      <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fill, minmax(180px, 1fr))', gap: '16px' }}>
        <StatCard label="Total Earned" value={`$${provider.total_earnings.toFixed(2)}`} color="var(--success)" icon={TrendingUp} />
        <StatCard label={`Earned (${days}d)`} value={`$${provider.period_earnings.toFixed(2)}`} color="var(--accent)" icon={ArrowUpRight} />
        <StatCard label="Jobs Served" value={provider.total_jobs_served} sub={`${provider.period_jobs_served} in ${days}d`} icon={Cpu} />
        <StatCard label="Active Nodes" value={provider.active_nodes} sub={`${provider.total_nodes} total`} color="var(--success)" icon={Server} />
        <StatCard label="Total Spent" value={`$${consumer.total_spent.toFixed(2)}`} color="var(--error)" icon={ArrowDownRight} />
        <StatCard label="Balance" value={`$${wallet_balance.toFixed(2)}`} color="var(--accent)" icon={Wallet} />
      </div>

      {/* --- Earnings Chart --- */}
      <div className="glass-card">
        <div className="card-header">
          <h3>Earnings Over Time</h3>
          <span style={{ fontSize: '12px', color: 'var(--text-muted)' }}>Last {days} days</span>
        </div>
        {provider.earnings_by_day.length > 0 ? (
          <div style={{ width: '100%', height: 280 }}>
            <ResponsiveContainer>
              <AreaChart data={provider.earnings_by_day} margin={{ top: 10, right: 10, left: 0, bottom: 0 }}>
                <defs>
                  <linearGradient id="earningsGrad" x1="0" y1="0" x2="0" y2="1">
                    <stop offset="5%" stopColor="#d4a037" stopOpacity={0.3} />
                    <stop offset="95%" stopColor="#d4a037" stopOpacity={0.0} />
                  </linearGradient>
                </defs>
                <CartesianGrid strokeDasharray="3 3" stroke="rgba(255,255,255,0.06)" />
                <XAxis dataKey="date" tick={{ fill: 'var(--text-muted)', fontSize: 11 }} tickFormatter={(v) => v.slice(5)} />
                <YAxis tick={{ fill: 'var(--text-muted)', fontSize: 11 }} tickFormatter={(v) => `$${v}`} />
                <Tooltip content={<ChartTooltip />} />
                <Area type="monotone" dataKey="earned" name="Earned ($)" stroke="#d4a037" fillOpacity={1} fill="url(#earningsGrad)" strokeWidth={2} />
              </AreaChart>
            </ResponsiveContainer>
          </div>
        ) : (
          <div className="empty-state" style={{ padding: '60px 0' }}>
            <TrendingUp size={40} style={{ color: 'var(--accent)', opacity: 0.3 }} />
            <p>No earnings data yet. Start your agent to earn credits!</p>
          </div>
        )}
      </div>

      {/* --- Jobs per Day + Model Breakdown --- */}
      <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '20px' }}>
        {/* Jobs per day bar chart */}
        <div className="glass-card">
          <div className="card-header"><h3>Jobs Served / Day</h3></div>
          {provider.earnings_by_day.length > 0 ? (
            <div style={{ width: '100%', height: 220 }}>
              <ResponsiveContainer>
                <BarChart data={provider.earnings_by_day} margin={{ top: 10, right: 10, left: 0, bottom: 0 }}>
                  <CartesianGrid strokeDasharray="3 3" stroke="rgba(255,255,255,0.06)" />
                  <XAxis dataKey="date" tick={{ fill: 'var(--text-muted)', fontSize: 11 }} tickFormatter={(v) => v.slice(5)} />
                  <YAxis tick={{ fill: 'var(--text-muted)', fontSize: 11 }} allowDecimals={false} />
                  <Tooltip content={<ChartTooltip />} />
                  <Bar dataKey="jobs" name="Jobs" fill="#d4a037" radius={[4, 4, 0, 0]} />
                </BarChart>
              </ResponsiveContainer>
            </div>
          ) : (
            <div className="empty-state"><p>No data</p></div>
          )}
        </div>

        {/* Model breakdown pie */}
        <div className="glass-card">
          <div className="card-header"><h3>Model Breakdown</h3></div>
          {provider.model_breakdown.length > 0 ? (
            <div style={{ display: 'flex', alignItems: 'center', gap: '20px' }}>
              <div style={{ width: 160, height: 160 }}>
                <ResponsiveContainer>
                  <PieChart>
                    <Pie data={provider.model_breakdown} dataKey="jobs" nameKey="model" cx="50%" cy="50%" outerRadius={70} strokeWidth={0}>
                      {provider.model_breakdown.map((_: any, i: number) => (
                        <Cell key={i} fill={CHART_COLORS[i % CHART_COLORS.length]} />
                      ))}
                    </Pie>
                    <Tooltip content={<ChartTooltip />} />
                  </PieChart>
                </ResponsiveContainer>
              </div>
              <div style={{ flex: 1, display: 'flex', flexDirection: 'column', gap: '8px' }}>
                {provider.model_breakdown.map((m: any, i: number) => (
                  <div key={m.model} style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
                    <div style={{ width: 10, height: 10, borderRadius: '50%', background: CHART_COLORS[i % CHART_COLORS.length] }} />
                    <span style={{ fontSize: '12px', color: 'var(--text-primary)', flex: 1 }}>{m.model}</span>
                    <span style={{ fontSize: '12px', color: 'var(--text-muted)' }}>{m.jobs} jobs</span>
                    <span style={{ fontSize: '12px', color: 'var(--success)' }}>${m.earned.toFixed(2)}</span>
                  </div>
                ))}
              </div>
            </div>
          ) : (
            <div className="empty-state"><p>No models served yet</p></div>
          )}
        </div>
      </div>

      {/* --- Transaction History --- */}
      <div className="glass-card">
        <div className="card-header">
          <h3>Transaction History</h3>
          <div style={{ display: 'flex', gap: '8px', alignItems: 'center' }}>
            <Filter size={14} style={{ color: 'var(--text-muted)' }} />
            <select
              value={txFilter}
              onChange={e => setTxFilter(e.target.value)}
              style={{
                background: 'rgba(255,255,255,0.05)', border: '1px solid var(--border)',
                color: 'var(--text-primary)', borderRadius: '6px', padding: '4px 8px', fontSize: '11px'
              }}
            >
              <option value="all">All Transactions</option>
              <option value="earning">Earnings Only</option>
              <option value="spending">Spending Only</option>
            </select>
          </div>
        </div>
        {filteredTx.length > 0 ? (
          <div style={{ display: 'flex', flexDirection: 'column', gap: '6px', maxHeight: '350px', overflowY: 'auto' }}>
            {filteredTx.map((tx: any) => (
              <div key={tx.id} style={{
                display: 'flex', justifyContent: 'space-between', alignItems: 'center',
                padding: '10px 12px', borderRadius: '8px',
                background: 'rgba(255,255,255,0.02)', border: '1px solid var(--border)'
              }}>
                <div style={{ display: 'flex', alignItems: 'center', gap: '10px' }}>
                  <div style={{
                    width: 28, height: 28, borderRadius: '50%',
                    background: tx.type === 'earning' ? 'rgba(34,197,94,0.15)' : 'rgba(239,68,68,0.15)',
                    display: 'flex', alignItems: 'center', justifyContent: 'center'
                  }}>
                    {tx.type === 'earning'
                      ? <ArrowUpRight size={14} style={{ color: 'var(--success)' }} />
                      : <ArrowDownRight size={14} style={{ color: 'var(--error)' }} />
                    }
                  </div>
                  <div>
                    <div style={{ fontSize: '13px', color: 'var(--text-primary)' }}>{tx.description}</div>
                    <div style={{ fontSize: '11px', color: 'var(--text-muted)' }}>
                      {new Date(tx.created_at).toLocaleString()}
                    </div>
                  </div>
                </div>
                <div style={{
                  fontSize: '14px', fontWeight: 700,
                  color: tx.type === 'earning' ? 'var(--success)' : 'var(--error)'
                }}>
                  {tx.type === 'earning' ? '+' : ''}{tx.amount > 0 ? `+$${tx.amount.toFixed(2)}` : `-$${Math.abs(tx.amount).toFixed(2)}`}
                </div>
              </div>
            ))}
          </div>
        ) : (
          <div className="empty-state">
            <p>No transactions yet</p>
          </div>
        )}
      </div>
    </div>
  );
};


/* ===== MAIN DASHBOARD ===== */
export const Dashboard: React.FC = () => {
  const { user, token, logout } = useAuth();
  const { balance } = useDashboard();
  const [activeTab, setActiveTab] = useState(() => {
    const params = new URLSearchParams(window.location.search);
    return params.get('tab') || 'overview';
  });

  if (!user) return <div style={{ padding: '100px', textAlign: 'center', color: 'var(--text-muted)' }}>Loading...</div>;

  return (
    <div className="dashboard-container">
      <aside className="dashboard-sidebar">
        <div className="sidebar-nav">
          <SidebarItem icon={LayoutDashboard} label="Overview" active={activeTab === 'overview'} onClick={() => setActiveTab('overview')} />
          <SidebarItem icon={TrendingUp} label="Provider" active={activeTab === 'provider'} onClick={() => setActiveTab('provider')} />
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
          <WalletCard balance={balance || 0} onRefresh={() => {}} />

          <StatCard label="Credits Earned" value={`$${Math.max(0, (balance || 0) - 100 + (100 - (balance || 0) < 0 ? 0 : 100 - (balance || 0))).toFixed(0)}`} sub="from providing" color="var(--success)" icon={TrendingUp} />

          <StatCard label="Cost Per Job" value="$1.00" sub="per inference" />

          <div className="grid-full-width">
            {activeTab === 'overview' && (
              <div className="overview-grid">
                <JobSubmitter />
                <div style={{ display: 'flex', flexDirection: 'column', gap: '20px' }}>
                  <JobHistory />
                  <NodesPanel />
                  <LiveModels />
                </div>
              </div>
            )}

            {activeTab === 'provider' && (
              <ProviderDashboard token={token} />
            )}

            {activeTab === 'wallet' && (
              <div className="glass-card">
                <h3>Wallet Details</h3>
                <div style={{ display: 'flex', gap: '40px', marginTop: '20px' }}>
                  <div>
                    <div style={{ fontSize: '12px', color: 'var(--text-muted)', textTransform: 'uppercase', marginBottom: '4px' }}>Current Balance</div>
                    <div style={{ fontSize: '2rem', fontWeight: 700, color: 'var(--accent)' }}>${(balance || 0).toFixed(2)}</div>
                  </div>
                  <div>
                    <div style={{ fontSize: '12px', color: 'var(--text-muted)', textTransform: 'uppercase', marginBottom: '4px' }}>Starting Balance</div>
                    <div style={{ fontSize: '2rem', fontWeight: 700, color: 'var(--text-primary)' }}>$100.00</div>
                  </div>
                </div>
                <p style={{ color: 'var(--text-muted)', fontSize: '13px', marginTop: '16px' }}>
                  Each inference job costs 1.00 credit. Providers earn $0.80 per completed job. Credits are deducted on submission.
                </p>
              </div>
            )}

            {activeTab === 'network' && (
              <div style={{ display: 'flex', flexDirection: 'column', gap: '20px' }}>
                <NodesPanel />
                <LiveModels />
              </div>
            )}
          </div>
        </div>
      </main>
    </div>
  );
};
