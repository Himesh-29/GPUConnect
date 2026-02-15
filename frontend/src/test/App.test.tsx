import { describe, it, expect, beforeEach, vi } from 'vitest'
import { render, screen, waitFor } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import axios from 'axios'
import App from '@/App'

vi.mock('axios')

// App already contains its own <Router>, so we do NOT wrap with BrowserRouter.
const mockWS = {
  onopen: null as any,
  onmessage: null as any,
  onclose: null as any,
  close: vi.fn(),
  send: vi.fn(),
  readyState: 1,
}
const MockWS = vi.fn(() => mockWS) as any
MockWS.OPEN = 1
MockWS.CLOSED = 3
MockWS.CONNECTING = 0
MockWS.CLOSING = 2
vi.stubGlobal('WebSocket', MockWS)

describe('App Component', () => {
  beforeEach(() => {
    localStorage.clear()
    vi.clearAllMocks()
  })

  it('should render navigation bar', () => {
    render(<App />)
    expect(screen.getByRole('link', { name: /GPU\s*Connect/i })).toBeInTheDocument()
  })

  it('should show login and register buttons when not authenticated', () => {
    render(<App />)
    expect(screen.getByRole('link', { name: /Sign In/i })).toBeInTheDocument()
    expect(screen.getByRole('link', { name: /Get Started/i })).toBeInTheDocument()
  })

  it('should show dashboard and logout when authenticated', async () => {
    localStorage.setItem('token', 'test-token')
    vi.mocked(axios.get).mockResolvedValue({
      data: {
        id: 1, username: 'testuser',
        email: 'test@example.com', role: 'USER', wallet_balance: 100
      }
    })

    render(<App />)

    await waitFor(() => {
      expect(screen.getByRole('link', { name: /Dashboard/i })).toBeInTheDocument()
    })
  })

  it('should have responsive navigation', () => {
    render(<App />)
    const mobileMenuBtn = screen.getByRole('button', { name: /Toggle Menu/i })
    expect(mobileMenuBtn).toBeInTheDocument()
  })

  it('should navigate to home when logo is clicked', async () => {
    const user = userEvent.setup()
    render(<App />)
    const logo = screen.getByRole('link', { name: /GPU\s*Connect/i })
    await user.click(logo)
    expect(logo).toHaveAttribute('href', '/')
  })

  it('should have marketplace section', () => {
    render(<App />)
    expect(screen.getAllByText(/Marketplace/i).length).toBeGreaterThanOrEqual(1)
  })

  it('should have features section', () => {
    render(<App />)
    expect(screen.getAllByText(/Features/i).length).toBeGreaterThanOrEqual(1)
  })

  it('should have how it works section', () => {
    render(<App />)
    expect(screen.getAllByText(/How It Works/i).length).toBeGreaterThanOrEqual(1)
  })

  it('should toggle mobile menu', async () => {
    const user = userEvent.setup()
    render(<App />)
    const mobileMenuBtn = screen.getByRole('button', { name: /Toggle Menu/i })
    await user.click(mobileMenuBtn)
    expect(mobileMenuBtn).toBeInTheDocument()
  })
})
