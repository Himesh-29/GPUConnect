import { describe, it, expect, beforeEach, vi } from 'vitest'
import { render, screen, waitFor } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import axios from 'axios'
import { Dashboard } from '@/pages/Dashboard'
import { BrowserRouter } from 'react-router-dom'
import { AuthProvider } from '@/context/AuthContext'
import { DashboardProvider } from '@/context/DashboardContext'

vi.mock('axios')

const mockWS = {
  onopen: null as any,
  onmessage: null as any,
  onclose: null as any,
  close: vi.fn(),
  send: vi.fn(),
  readyState: 1,
}
vi.stubGlobal('WebSocket', vi.fn(() => mockWS))

const profileData = {
  id: 1,
  username: 'testuser',
  email: 'test@example.com',
  role: 'PROVIDER',
  wallet_balance: 100
}

const renderDashboard = async () => {
  localStorage.setItem('token', 'test-token')
  vi.mocked(axios.get).mockResolvedValue({ data: profileData })

  const result = render(
    <BrowserRouter>
      <AuthProvider>
        <DashboardProvider>
          <Dashboard />
        </DashboardProvider>
      </AuthProvider>
    </BrowserRouter>
  )

  // Wait until AuthContext finishes loading (Dashboard shows "Loading..." until user is set)
  await waitFor(() => {
    expect(screen.queryByText('Loading...')).not.toBeInTheDocument()
  })

  return result
}

describe('Dashboard Page', () => {
  beforeEach(() => {
    localStorage.clear()
    vi.clearAllMocks()
  })

  it('should render dashboard sidebar with navigation', async () => {
    await renderDashboard()
    // Sidebar has buttons: Overview, Provider, Wallet, Network
    const buttons = screen.getAllByRole('button')
    const labels = buttons.map(b => b.textContent?.trim())
    expect(labels).toContain('Overview')
    expect(labels).toContain('Provider')
    expect(labels).toContain('Wallet')
    expect(labels).toContain('Network')
  })

  it('should have sidebar navigation buttons', async () => {
    await renderDashboard()
    const buttons = screen.getAllByRole('button')
    const hasOverview = buttons.some(btn => btn.textContent?.includes('Overview'))
    const hasProvider = buttons.some(btn => btn.textContent?.includes('Provider'))
    expect(hasOverview).toBe(true)
    expect(hasProvider).toBe(true)
  })

  it('should switch to provider tab', async () => {
    const user = userEvent.setup()
    await renderDashboard()

    const providerTab = screen.getAllByRole('button').find(b => b.textContent?.includes('Provider'))
    expect(providerTab).toBeDefined()
    if (providerTab) {
      await user.click(providerTab)
      expect(providerTab.className).toContain('active')
    }
  })

  it('should display wallet card with Total Balance', async () => {
    await renderDashboard()
    expect(screen.getByText(/Total Balance/i)).toBeInTheDocument()
  })

  it('should show user info in sidebar', async () => {
    await renderDashboard()
    expect(screen.getByText('testuser')).toBeInTheDocument()
  })

  it('should have sign out button', async () => {
    await renderDashboard()
    expect(screen.getByText('Sign Out')).toBeInTheDocument()
  })

  it('should call axios.get for profile', async () => {
    await renderDashboard()
    expect(vi.mocked(axios.get)).toHaveBeenCalled()
  })
})
