import React, { useState, useEffect } from 'react';
import axios from 'axios';
import { useAuth } from '../context/AuthContext';
import { useDashboard } from '../context/DashboardContext';
import { Zap, Loader2 } from 'lucide-react';

const API_URL = import.meta.env.VITE_API_URL || 'http://localhost:8000';

const JobSubmitter: React.FC = () => {
    const { token } = useAuth();
    const { models, recentJobs, loading: loadingModels } = useDashboard();
    const [prompt, setPrompt] = useState('');
    const [model, setModel] = useState('');
    const [status, setStatus] = useState('');
    const [result, setResult] = useState('');
    const [submitting, setSubmitting] = useState(false);
    const [activeJobId, setActiveJobId] = useState<number | null>(null);

    // Auto-select first model if none selected
    useEffect(() => {
        if (!model && models.length > 0) {
            setModel(models[0].name);
        }
    }, [models, model]);

    // Monitor active job status via streaming recentJobs
    useEffect(() => {
        if (activeJobId) {
            const job = recentJobs.find(j => j.id === activeJobId);
            if (job) {
                if (job.status === 'COMPLETED') {
                    setStatus(`✅ Job #${activeJobId} completed`);
                    setResult(job.result?.output || JSON.stringify(job.result));
                    setActiveJobId(null);
                } else if (job.status === 'FAILED') {
                    setStatus(`❌ Job #${activeJobId} failed`);
                    setResult(job.result?.error || 'Unknown error');
                    setActiveJobId(null);
                } else if (job.status === 'RUNNING') {
                    setStatus(`⚙️ Job #${activeJobId} is running...`);
                }
            }
        }
    }, [recentJobs, activeJobId]);

    const handleSubmit = async () => {
        if (!prompt.trim()) { setStatus('Please enter a prompt.'); return; }
        if (!model) { setStatus('No models available. Wait for a GPU node to connect.'); return; }

        setSubmitting(true);
        setStatus('Submitting...');
        setResult('');

        try {
            const response = await axios.post(
                `${API_URL}/api/computing/submit-job/`,
                { prompt, model },
                { headers: { Authorization: `Bearer ${token}` } }
            );
            const jobId = response.data.job_id;
            setActiveJobId(jobId);
            setStatus(`Job #${jobId} submitted — waiting for result...`);
        } catch (err: any) {
            setStatus(`Error: ${err.response?.data?.error || err.message}`);
        }
        setSubmitting(false);
    };

    return (
        <div className="glass-card">
            <div className="card-header">
                <h3>Submit a Job</h3>
                {models.length > 0 && (
                    <span style={{
                        fontSize: '12px', color: 'var(--success)',
                        display: 'flex', alignItems: 'center', gap: '4px'
                    }}>
                        <span style={{ width: 6, height: 6, borderRadius: '50%', background: 'var(--success)', display: 'inline-block' }} />
                        {models.length} model{models.length > 1 ? 's' : ''} online
                    </span>
                )}
            </div>

            <div style={{ display: 'flex', flexDirection: 'column', gap: '12px' }}>
                {/* Model selector */}
                <select
                    className="input-field"
                    value={model}
                    onChange={(e) => setModel(e.target.value)}
                    disabled={loadingModels || models.length === 0}
                >
                    {loadingModels ? (
                        <option>Loading models...</option>
                    ) : models.length === 0 ? (
                        <option>No nodes connected</option>
                    ) : (
                        models.map(m => (
                            <option key={m.name} value={m.name}>
                                {m.name} — {m.providers} node{m.providers > 1 ? 's' : ''}
                            </option>
                        ))
                    )}
                </select>

                {/* Prompt */}
                <textarea
                    className="input-field"
                    placeholder="Enter your prompt..."
                    value={prompt}
                    onChange={(e) => setPrompt(e.target.value)}
                    rows={3}
                    style={{ resize: 'vertical' }}
                />

                {/* Submit */}
                <button
                    className="btn-primary"
                    onClick={handleSubmit}
                    disabled={submitting || !!activeJobId || !prompt.trim() || !model}
                    style={{
                        width: '100%',
                        display: 'flex', alignItems: 'center', justifyContent: 'center', gap: '8px',
                        cursor: (submitting || !!activeJobId || !prompt.trim() || !model) ? 'not-allowed' : 'pointer',
                        opacity: (submitting || !!activeJobId || !prompt.trim() || !model) ? 0.7 : 1
                    }}
                >
                    {models.length === 0 ? (
                        <><Zap size={16} className="opacity-50" /> No Nodes Connected</>
                    ) : (submitting || !!activeJobId) ? (
                        <><Loader2 size={16} className="spin" /> Processing...</>
                    ) : (
                        <><Zap size={16} /> Submit Job (1 Credit)</>
                    )}
                </button>

                {/* Status */}
                {status && (
                    <div style={{
                        padding: '10px 14px', borderRadius: '8px', fontSize: '13px',
                        background: status.includes('Error') || status.includes('❌')
                            ? 'rgba(239,68,68,0.1)' : status.includes('✅')
                            ? 'rgba(34,197,94,0.1)' : 'rgba(212,160,55,0.08)',
                        border: '1px solid var(--border)',
                        color: status.includes('Error') || status.includes('❌')
                            ? 'var(--error)' : status.includes('✅')
                            ? 'var(--success)' : 'var(--text-secondary)',
                    }}>
                        {status}
                    </div>
                )}

                {/* Result */}
                {result && (
                    <div style={{
                        padding: '16px', borderRadius: '8px',
                        background: 'rgba(0,0,0,0.3)',
                        border: '1px solid var(--border-accent)',
                        whiteSpace: 'pre-wrap', fontSize: '13px',
                        color: 'var(--text-primary)', lineHeight: '1.6',
                        maxHeight: '300px', overflowY: 'auto'
                    }}>
                        <div style={{
                            fontSize: '11px', color: 'var(--accent)',
                            textTransform: 'uppercase', letterSpacing: '1px',
                            marginBottom: '8px', fontWeight: 600
                        }}>
                            LLM Response
                        </div>
                        {result}
                    </div>
                )}
            </div>
        </div>
    );
};

export default JobSubmitter;
