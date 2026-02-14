import React, { createContext, useContext, useEffect, useState, useRef } from 'react';
import { useAuth } from './AuthContext';

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
}

interface DashboardContextType {
  stats: DashboardStats | null;
  models: ModelInfo[];
  balance: number | null;
  recentJobs: JobInfo[];
  loading: boolean;
}

const DashboardContext = createContext<DashboardContextType>({
  stats: null,
  models: [],
  balance: null,
  recentJobs: [],
  loading: true
});

export const useDashboard = () => useContext(DashboardContext);

export const DashboardProvider: React.FC<{ children: React.ReactNode }> = ({ children }) => {
  const { token, user } = useAuth();
  const [stats, setStats] = useState<DashboardStats | null>(null);
  const [models, setModels] = useState<ModelInfo[]>([]);
  const [balance, setBalance] = useState<number | null>(null);
  const [recentJobs, setRecentJobs] = useState<JobInfo[]>([]);
  const [loading, setLoading] = useState(true);
  
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
    }
  };

  useEffect(() => {
    connect();
    return () => {
      if (ws.current) ws.current.close();
      if (reconnectTimeout.current) clearTimeout(reconnectTimeout.current);
    };
  }, [token]); // Reconnect if token changes (login/logout)

  // Sync initial balance from Auth if available
  useEffect(() => {
    if (user && balance === null) {
      setBalance(Number(user.wallet_balance));
    }
  }, [user]);

  return (
    <DashboardContext.Provider value={{ stats, models, balance, recentJobs, loading }}>
      {children}
    </DashboardContext.Provider>
  );
};
