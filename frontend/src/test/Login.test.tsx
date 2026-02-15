import { describe, it, expect, beforeEach, vi } from 'vitest'
import { render, screen, fireEvent, waitFor } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import axios from 'axios'
import { Login } from '@/pages/Login'
import { BrowserRouter } from 'react-router-dom'
import { AuthProvider } from '@/context/AuthContext'

vi.mock('axios')

const renderLogin = () => {
  return render(
    <BrowserRouter>
      <AuthProvider>
        <Login />
      </AuthProvider>
    </BrowserRouter>
  )
}

describe('Login Page', () => {
  beforeEach(() => {
    localStorage.clear()
    vi.clearAllMocks()
  })

  it('should render login form', () => {
    renderLogin()
    expect(screen.getByPlaceholderText('Username')).toBeInTheDocument()
    expect(screen.getByPlaceholderText('Password')).toBeInTheDocument()
    expect(screen.getByRole('button', { name: /Sign In/i })).toBeInTheDocument()
  })

  it('should show OAuth buttons', () => {
    renderLogin()
    expect(screen.getByText(/Continue with Google/i)).toBeInTheDocument()
    expect(screen.getByText(/Continue with GitHub/i)).toBeInTheDocument()
  })

  it('should handle successful login', async () => {
    vi.mocked(axios.post).mockResolvedValue({
      data: { access: 'test-token-123' }
    })

    const user = userEvent.setup()
    renderLogin()

    await user.type(screen.getByPlaceholderText('Username'), 'testuser')
    await user.type(screen.getByPlaceholderText('Password'), 'password123')
    await user.click(screen.getByRole('button', { name: /Sign In/i }))

    await waitFor(() => {
      expect(vi.mocked(axios.post)).toHaveBeenCalledWith(
        expect.stringContaining('/api/core/token/'),
        { username: 'testuser', password: 'password123' }
      )
    })
  })

  it('should show error message on failed login', async () => {
    vi.mocked(axios.post).mockRejectedValue({
      response: { data: { detail: 'Invalid credentials' } }
    })

    const user = userEvent.setup()
    renderLogin()

    await user.type(screen.getByPlaceholderText('Username'), 'testuser')
    await user.type(screen.getByPlaceholderText('Password'), 'wrongpass')
    await user.click(screen.getByRole('button', { name: /Sign In/i }))

    await waitFor(() => {
      expect(screen.getByText(/Invalid credentials/i)).toBeInTheDocument()
    })
  })

  it('should populate form fields correctly', async () => {
    const user = userEvent.setup()
    renderLogin()

    const usernameInput = screen.getByPlaceholderText('Username') as HTMLInputElement
    const passwordInput = screen.getByPlaceholderText('Password') as HTMLInputElement

    await user.type(usernameInput, 'testuser')
    await user.type(passwordInput, 'testpass')

    expect(usernameInput.value).toBe('testuser')
    expect(passwordInput.value).toBe('testpass')
  })

  it('should have signup link', () => {
    renderLogin()
    expect(screen.getByText(/Don't have an account/i)).toBeInTheDocument()
    expect(screen.getByRole('link', { name: /Create one/i })).toBeInTheDocument()
  })
})
