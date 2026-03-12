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
  streamed_text?: string;
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
  // Keep a ref that always reflects the latest activeSessionId to avoid stale closures
  const activeSessionIdRef = useRef<string>('default');
  const _setActiveSessionId = (id: string) => {
    activeSessionIdRef.current = id;
    setActiveSessionId(id);
  };

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

  // Distribute incoming recentJobs into sessions (fully immutable updates)
  useEffect(() => {
    if (recentJobs.length === 0) return;

    setSessions(prev => {
      if (prev.length === 0) return prev;

      // Index recent jobs by id for O(1) status sync
      const recentJobsById = new Map(recentJobs.map(j => [j.id, j]));

      // Collect all job ids already tracked in any session
      const allMappedJobIds = new Set(prev.flatMap(s => s.jobs.map(j => j.id)));

      // Only consider jobs we haven't seen before
      const newJobs = recentJobs.filter(j => !allMappedJobIds.has(j.id));

      // Determine target session for each new job
      const newJobsBySessionId = new Map<string, any[]>();
      const fallbackSessionId = activeSessionIdRef.current || prev[0]?.id;
      newJobs.forEach(newJob => {
        const targetId = newJob.session_id ? String(newJob.session_id) : fallbackSessionId;
        if (!targetId) return;
        const list = newJobsBySessionId.get(targetId) || [];
        list.push(newJob);
        newJobsBySessionId.set(targetId, list);
      });

      // Build a new sessions array with new session/job objects
      return prev.map(session => {
        // Sync updated jobs (status changes) immutably
        const syncedJobs = session.jobs.map(localJob => {
          const updated = recentJobsById.get(localJob.id);
          return updated ? updated : localJob;
        });
        // Append new jobs belonging to this session
        const extraJobs = newJobsBySessionId.get(session.id) || [];
        if (extraJobs.length === 0 && syncedJobs.every((j, i) => j === session.jobs[i])) {
          return session; // no changes — keep same reference
        }
        return { ...session, jobs: [...syncedJobs, ...extraJobs] };
      });
    });
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
      case 'job_stream':
        setSessions(prev =>
          prev.map(session => {
            const jobIndex = session.jobs.findIndex((j: any) => j.id === msg.task_id);
            if (jobIndex === -1) return session;
            const oldJob = session.jobs[jobIndex];
            const updatedJob = {
              ...oldJob,
              streamed_text: (oldJob.streamed_text || '') + msg.chunk,
            };
            return {
              ...session,
              jobs: [
                ...session.jobs.slice(0, jobIndex),
                updatedJob,
                ...session.jobs.slice(jobIndex + 1),
              ],
            };
          })
        );
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
    <DashboardContext.Provider value={{ stats, models, balance, recentJobs, providerStats, setProviderDays, loading, sessions, setSessions, activeSessionId, setActiveSessionId: _setActiveSessionId }}>
      {children}
    </DashboardContext.Provider>
  );
};
