import { describe, it, expect, beforeEach, vi } from 'vitest'
import { render, screen, waitFor } from '@testing-library/react'
import { DashboardProvider, useDashboard } from '@/context/DashboardContext'
import { AuthProvider } from '@/context/AuthContext'
import React from 'react'
import axios from 'axios'

vi.mock('axios')

let mockWS: any
const MockWebSocket = vi.fn(() => {
  mockWS = {
    onopen: null as any,
    onmessage: null as any,
    onclose: null as any,
    close: vi.fn(),
    send: vi.fn(),
    readyState: 1,
  }
  return mockWS
}) as any
MockWebSocket.OPEN = 1
MockWebSocket.CLOSED = 3
MockWebSocket.CONNECTING = 0
MockWebSocket.CLOSING = 2
vi.stubGlobal('WebSocket', MockWebSocket)

const TestDashboardComponent = () => {
  const { stats, models, balance, recentJobs, loading } = useDashboard()
  return (
    <div>
      <div data-testid="loading">{loading ? 'loading' : 'ready'}</div>
      <div data-testid="stats">{stats?.active_nodes ?? 'no-stats'}</div>
      <div data-testid="models">{models.length}</div>
      <div data-testid="balance">{balance !== null ? balance : 'no-balance'}</div>
      <div data-testid="jobs">{recentJobs.length}</div>
    </div>
  )
}

describe('DashboardContext', () => {
  beforeEach(() => {
    localStorage.clear()
    vi.clearAllMocks()
    vi.mocked(axios.get).mockResolvedValue({
      data: {
        id: 1, username: 'testuser',
        email: 'test@example.com', role: 'USER', wallet_balance: 50
      }
    })
  })

  it('should provide dashboard context', () => {
    render(
      <AuthProvider>
        <DashboardProvider>
          <TestDashboardComponent />
        </DashboardProvider>
      </AuthProvider>
    )
    expect(screen.getByTestId('models')).toBeInTheDocument()
  })

  it('should initialize with loading state', () => {
    render(
      <AuthProvider>
        <DashboardProvider>
          <TestDashboardComponent />
        </DashboardProvider>
      </AuthProvider>
    )
    expect(screen.getByTestId('loading')).toHaveTextContent('loading')
  })

  it('should connect via WebSocket on mount', async () => {
    // DashboardProvider calls connect() in useEffect on mount
    // The connect() function calls `new WebSocket(url)` immediately (regardless of token)
    render(
      <AuthProvider>
        <DashboardProvider>
          <TestDashboardComponent />
        </DashboardProvider>
      </AuthProvider>
    )

    await waitFor(() => {
      expect(MockWebSocket).toHaveBeenCalled()
    })
  })

  it('should have default empty values', () => {
    render(
      <AuthProvider>
        <DashboardProvider>
          <TestDashboardComponent />
        </DashboardProvider>
      </AuthProvider>
    )
    expect(screen.getByTestId('models')).toHaveTextContent('0')
    expect(screen.getByTestId('jobs')).toHaveTextContent('0')
  })
})
