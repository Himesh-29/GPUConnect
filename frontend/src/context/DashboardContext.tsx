import React, { createContext, useContext, useEffect, useState, useRef } from 'react';
import { useAuth } from './AuthContext';
import axios from 'axios';

const WS_URL = import.meta.env.VITE_WS_URL || 'ws://localhost:8000/ws/dashboard/';

interface DashboardStats {
  active_nodes: number;
  completed_jobs: number;
  available_models: number;
}

interface ModelInfo {
  name: string;
  providers: number;
}

interface JobInfo {
  id: number;
  status: string;
  prompt: string;
  model: string;
  cost: string | null;
  result: any;
  created_at: string;
  completed_at: string | null;
  session_id?: string;
}

export interface ChatSession {
  id: string;
  name: string;
  jobs: JobInfo[];
}

interface DashboardContextType {
  stats: DashboardStats | null;
  models: ModelInfo[];
  balance: number | null;
  recentJobs: JobInfo[];
  providerStats: any | null;
  setProviderDays: (days: number) => void;
  loading: boolean;
  sessions: ChatSession[];
  setSessions: React.Dispatch<React.SetStateAction<ChatSession[]>>;
  activeSessionId: string;
  setActiveSessionId: (id: string) => void;
}

const DashboardContext = createContext<DashboardContextType>({
  stats: null,
  models: [],
  balance: null,
  recentJobs: [],
  providerStats: null,
  setProviderDays: () => {},
  loading: true,
  sessions: [],
  setSessions: () => {},
  activeSessionId: 'default',
  setActiveSessionId: () => {}
});

export const useDashboard = () => useContext(DashboardContext);

export const DashboardProvider: React.FC<{ children: React.ReactNode }> = ({ children }) => {
  const { token, user } = useAuth();
  const [stats, setStats] = useState<DashboardStats | null>(null);
  const [models, setModels] = useState<ModelInfo[]>([]);
  const [balance, setBalance] = useState<number | null>(null);
  const [recentJobs, setRecentJobs] = useState<JobInfo[]>([]);
  const [providerStats, setProviderStats] = useState<any | null>(null);
  const [loading, setLoading] = useState(true);
  
  // Chat Sessions global state
  const [sessions, setSessions] = useState<ChatSession[]>([
    { id: 'default', name: 'New Chat', jobs: [] }
  ]);
  const [activeSessionId, setActiveSessionId] = useState<string>('default');

  // Fetch sessions from REST
  useEffect(() => {
    if (!token) return;
    const fetchSessions = async () => {
      try {
        const res = await axios.get(`${import.meta.env.VITE_API_URL || 'http://localhost:8000'}/api/computing/sessions/`, {
          headers: { Authorization: `Bearer ${token}` }
        });
        const backendSessions = res.data.map((s: any) => ({
          ...s,
          jobs: s.jobs || []
        }));
        setSessions(prev => {
          const def = prev.find(p => p.id === 'default');
          return def ? [def, ...backendSessions] : backendSessions;
        });
      } catch (err) {
        console.error('Failed to fetch sessions', err);
      }
    };
    fetchSessions();
  }, [token]);

  // Distribute incoming recentJobs into the active session
  useEffect(() => {
    if (recentJobs.length === 0) return;
    
    setSessions(prev => {
      const next = [...prev];
      const allMappedJobIds = new Set(next.flatMap(s => s.jobs.map(j => j.id)));
      
      const newJobs = recentJobs.filter(j => !allMappedJobIds.has(j.id));
      if (newJobs.length > 0) {
        newJobs.forEach(newJob => {
          if (newJob.session_id) {
            const targetSession = next.find(s => s.id === newJob.session_id);
            if (targetSession) {
              targetSession.jobs.push(newJob);
            }
          } else {
            const activeSession = next.find(s => s.id === activeSessionId) || next[0];
            if (activeSession) activeSession.jobs.push(newJob);
          }
        });
      }

      // Sync updated jobs (status changes)
      next.forEach(session => {
        session.jobs = session.jobs.map(localJob => {
          const updatedFromServer = recentJobs.find(rj => rj.id === localJob.id);
          return updatedFromServer ? updatedFromServer : localJob;
        });
      });

      return next;
    });
  // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [recentJobs]);

  const ws = useRef<WebSocket | null>(null);
  const reconnectTimeout = useRef<any>(null);

  const connect = () => {
    if (ws.current?.readyState === WebSocket.OPEN) return;

    // Append token if available for private updates
    const url = token ? `${WS_URL}?token=${token}` : WS_URL;
    const socket = new WebSocket(url);

    socket.onopen = () => {
      console.log('Dashboard WS Connected');
      setLoading(false);
    };

    socket.onmessage = (event) => {
      try {
        const msg = JSON.parse(event.data);
        handleMessage(msg);
      } catch (err) {
        console.error('WS Parse Error', err);
      }
    };

    socket.onclose = () => {
      console.log('Dashboard WS Disconnected');
      // Reconnect after 3s
      reconnectTimeout.current = setTimeout(connect, 3000);
    };

    ws.current = socket;
  };

  const handleMessage = (msg: any) => {
    switch (msg.type) {
      case 'stats_update':
        setStats(msg.stats);
        break;
      case 'models_update':
        setModels(msg.models);
        break;
      case 'balance_update':
        setBalance(parseFloat(msg.balance));
        break;
      case 'jobs_update':
        // Initial bulk list
        setRecentJobs(msg.jobs);
        break;
      case 'job_update':
        // Single job update (prepend or update existing)
        setRecentJobs(prev => {
          const updatedJob = msg.job;
          const exists = prev.find(j => j.id === updatedJob.id);
          if (exists) {
            return prev.map(j => j.id === updatedJob.id ? updatedJob : j);
          } else {
            return [updatedJob, ...prev].slice(0, 10); // Keep last 10
          }
        });
        break;
      case 'provider_stats_update':
        setProviderStats(msg.stats);
        if (msg.stats?.wallet_balance !== undefined) {
          setBalance(msg.stats.wallet_balance);
        }
        break;
    }
  };

  const setProviderDays = (days: number) => {
    if (ws.current?.readyState === WebSocket.OPEN) {
      ws.current.send(JSON.stringify({
        type: 'subscribe_provider_stats',
        days: days
      }));
    }
  };

  useEffect(() => {
    connect();
    return () => {
      if (ws.current) ws.current.close();
      if (reconnectTimeout.current) clearTimeout(reconnectTimeout.current);
    };
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [token]); // Reconnect if token changes (login/logout)

  // Sync initial balance from Auth if available
  useEffect(() => {
    if (user && balance === null) {
      setBalance(Number(user.wallet_balance));
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [user]);

  return (
    <DashboardContext.Provider value={{ stats, models, balance, recentJobs, providerStats, setProviderDays, loading, sessions, setSessions, activeSessionId, setActiveSessionId }}>
      {children}
    </DashboardContext.Provider>
  );
};
