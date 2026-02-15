import { describe, it, expect, beforeEach, vi } from 'vitest'
import { render, screen, waitFor } from '@testing-library/react'
import axios from 'axios'
import JobSubmitter from '@/components/JobSubmitter'
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

const renderJobSubmitter = async () => {
  localStorage.setItem('token', 'test-token')
  vi.mocked(axios.get).mockResolvedValue({
    data: {
      id: 1, username: 'testuser',
      email: 'test@example.com', role: 'USER', wallet_balance: 100
    }
  })

  const result = render(
    <AuthProvider>
      <DashboardProvider>
        <JobSubmitter />
      </DashboardProvider>
    </AuthProvider>
  )

  // Wait for auth to finish loading
  await waitFor(() => {
    expect(screen.queryByText('Loading...')).not.toBeInTheDocument()
  })

  return result
}

describe('JobSubmitter Component', () => {
  beforeEach(() => {
    localStorage.clear()
    vi.clearAllMocks()
  })

  it('should render the job submitter card', async () => {
    await renderJobSubmitter()
    expect(screen.getByText('Submit a Job')).toBeInTheDocument()
  })

  it('should render prompt textarea', async () => {
    await renderJobSubmitter()
    expect(screen.getByPlaceholderText('Enter your prompt...')).toBeInTheDocument()
  })

  it('should have a submit button', async () => {
    await renderJobSubmitter()
    // When no models connected, button shows "No Nodes Connected"
    const btn = screen.getByRole('button')
    expect(btn).toBeInTheDocument()
  })

  it('should show model selector', async () => {
    await renderJobSubmitter()
    const select = screen.getByRole('combobox')
    expect(select).toBeInTheDocument()
  })

  it('should disable button when no models available', async () => {
    await renderJobSubmitter()
    const btn = screen.getByRole('button', { name: /No Nodes Connected/i })
    expect(btn).toBeDisabled()
  })
})
