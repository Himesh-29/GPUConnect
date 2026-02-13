import React, { useState, useEffect } from 'react';
import axios from 'axios';
import { useAuth } from '../context/AuthContext';
import { Zap, Loader2 } from 'lucide-react';

const API_URL = import.meta.env.VITE_API_URL || 'http://localhost:8000';

interface ModelInfo {
    name: string;
    providers: number;
}

const JobSubmitter: React.FC = () => {
    const { token } = useAuth();
    const [prompt, setPrompt] = useState('');
    const [model, setModel] = useState('');
    const [models, setModels] = useState<ModelInfo[]>([]);
    const [loadingModels, setLoadingModels] = useState(true);
    const [status, setStatus] = useState('');
    const [result, setResult] = useState('');
    const [polling, setPolling] = useState(false);

    useEffect(() => {
        fetchModels();
    }, []);

    const fetchModels = async () => {
        setLoadingModels(true);
        try {
            const resp = await axios.get(`${API_URL}/api/computing/models/`);
            setModels(resp.data.models || []);
            if (resp.data.models?.length > 0) {
                setModel(resp.data.models[0].name);
            }
        } catch {
            setModels([]);
        }
        setLoadingModels(false);
    };

    const handleSubmit = async () => {
        if (!prompt.trim()) { setStatus('Please enter a prompt.'); return; }
        if (!model) { setStatus('No models available. Wait for a GPU node to connect.'); return; }

        setStatus('Submitting...');
        setResult('');

        try {
            const response = await axios.post(
                `${API_URL}/api/computing/submit-job/`,
                { prompt, model },
                { headers: { Authorization: `Bearer ${token}` } }
            );
            setStatus(`Job #${response.data.job_id} submitted — waiting for result...`);
            pollJobResult(response.data.job_id);
        } catch (err: any) {
            setStatus(`Error: ${err.response?.data?.error || err.message}`);
        }
    };

    const pollJobResult = async (id: number) => {
        setPolling(true);
        for (let i = 0; i < 60; i++) {
            try {
                const resp = await axios.get(
                    `${API_URL}/api/computing/jobs/${id}/`,
                    { headers: { Authorization: `Bearer ${token}` } }
                );
                if (resp.data.status === 'COMPLETED') {
                    setStatus(`✅ Job #${id} completed`);
                    setResult(resp.data.result?.output || JSON.stringify(resp.data.result));
                    setPolling(false);
                    return;
                } else if (resp.data.status === 'FAILED') {
                    setStatus(`❌ Job #${id} failed`);
                    setResult(resp.data.result?.error || 'Unknown error');
                    setPolling(false);
                    return;
                }
            } catch { /* ignore */ }
            await new Promise(r => setTimeout(r, 2000));
        }
        setStatus(`⏱ Job #${id} timed out`);
        setPolling(false);
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
                    disabled={polling || !prompt.trim() || !model}
                    style={{
                        width: '100%',
                        display: 'flex', alignItems: 'center', justifyContent: 'center', gap: '8px'
                    }}
                >
                    {polling ? (
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
