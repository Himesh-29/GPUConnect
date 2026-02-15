import { describe, it, expect, beforeEach, vi } from 'vitest'
import { render, screen, fireEvent, waitFor } from '@testing-library/react'
import axios from 'axios'
import { AuthProvider, useAuth } from '@/context/AuthContext'
import React from 'react'

vi.mock('axios')

// Provide a working WebSocket mock so DashboardProvider (if nested) doesn't crash
const mockWS = {
  onopen: null as any,
  onmessage: null as any,
  onclose: null as any,
  close: vi.fn(),
  send: vi.fn(),
  readyState: 1,
}
vi.stubGlobal('WebSocket', vi.fn(() => mockWS))

const TestComponent = () => {
  const { user, token, login, logout, isAuthenticated, loading } = useAuth()
  return (
    <div>
      <div data-testid="loading">{loading ? 'loading' : 'ready'}</div>
      <div data-testid="authenticated">{isAuthenticated ? 'yes' : 'no'}</div>
      <div data-testid="token">{token || 'no-token'}</div>
      <div data-testid="username">{user?.username || 'no-user'}</div>
      <button onClick={() => login('test-token')}>Login</button>
      <button onClick={logout}>Logout</button>
    </div>
  )
}

describe('AuthContext', () => {
  beforeEach(() => {
    localStorage.clear()
    vi.clearAllMocks()
  })

  it('should render with initial state', () => {
    render(
      <AuthProvider>
        <TestComponent />
      </AuthProvider>
    )
    expect(screen.getByTestId('authenticated')).toHaveTextContent('no')
    expect(screen.getByTestId('token')).toHaveTextContent('no-token')
  })

  it('should handle login', async () => {
    vi.mocked(axios.get).mockResolvedValue({
      data: { id: 1, username: 'testuser', email: 'test@example.com', role: 'USER', wallet_balance: 100 }
    })

    render(
      <AuthProvider>
        <TestComponent />
      </AuthProvider>
    )

    fireEvent.click(screen.getByText('Login'))

    await waitFor(() => {
      expect(screen.getByTestId('authenticated')).toHaveTextContent('yes')
    })
    expect(localStorage.getItem('token')).toBe('test-token')
  })

  it('should handle logout', async () => {
    localStorage.setItem('token', 'test-token')
    vi.mocked(axios.get).mockResolvedValue({
      data: { id: 1, username: 'testuser', email: 'test@example.com', role: 'USER', wallet_balance: 100 }
    })

    render(
      <AuthProvider>
        <TestComponent />
      </AuthProvider>
    )

    await waitFor(() => {
      expect(screen.getByTestId('authenticated')).toHaveTextContent('yes')
    })

    fireEvent.click(screen.getByText('Logout'))

    await waitFor(() => {
      expect(screen.getByTestId('authenticated')).toHaveTextContent('no')
    })
    expect(localStorage.getItem('token')).toBeNull()
  })

  it('should fetch profile on token set', async () => {
    vi.mocked(axios.get).mockResolvedValue({
      data: { id: 1, username: 'testuser', email: 'test@example.com', role: 'USER', wallet_balance: 100 }
    })

    render(
      <AuthProvider>
        <TestComponent />
      </AuthProvider>
    )

    fireEvent.click(screen.getByText('Login'))
    await waitFor(() => {
      expect(vi.mocked(axios.get)).toHaveBeenCalled()
    })
  })

  it('should throw error when useAuth is used outside provider', () => {
    const spy = vi.spyOn(console, 'error').mockImplementation(() => {})
    expect(() => {
      render(<TestComponent />)
    }).toThrow('useAuth must be used within AuthProvider')
    spy.mockRestore()
  })
})
