import { describe, it, expect, beforeEach, vi } from 'vitest'
import { render, screen, waitFor } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import axios from 'axios'
import { Register } from '@/pages/Register'
import { BrowserRouter } from 'react-router-dom'
import { AuthProvider } from '@/context/AuthContext'

vi.mock('axios')

const renderRegister = () => {
  return render(
    <BrowserRouter>
      <AuthProvider>
        <Register />
      </AuthProvider>
    </BrowserRouter>
  )
}

describe('Register Page', () => {
  beforeEach(() => {
    localStorage.clear()
    vi.clearAllMocks()
  })

  it('should render registration form', () => {
    renderRegister()
    expect(screen.getByPlaceholderText('Username')).toBeInTheDocument()
    expect(screen.getByPlaceholderText('Email')).toBeInTheDocument()
    expect(screen.getByPlaceholderText(/Password/i)).toBeInTheDocument()
    expect(screen.getByRole('button', { name: /Create Account/i })).toBeInTheDocument()
  })

  it('should handle successful registration', async () => {
    vi.mocked(axios.post)
      .mockResolvedValueOnce({ data: { id: 1 } })
      .mockResolvedValueOnce({ data: { access: 'test-token-123' } })

    const user = userEvent.setup()
    renderRegister()

    await user.type(screen.getByPlaceholderText('Username'), 'newuser')
    await user.type(screen.getByPlaceholderText('Email'), 'new@example.com')
    await user.type(screen.getByPlaceholderText(/Password/i), 'password123')
    await user.click(screen.getByRole('button', { name: /Create Account/i }))

    await waitFor(() => {
      expect(vi.mocked(axios.post)).toHaveBeenCalledWith(
        expect.stringContaining('/api/core/register/'),
        expect.objectContaining({
          username: 'newuser',
          email: 'new@example.com',
          password: 'password123'
        })
      )
    })
  })

  it('should show error on registration failure', async () => {
    vi.mocked(axios.post).mockRejectedValue({
      response: { data: { username: ['Username already exists'] } }
    })

    const user = userEvent.setup()
    renderRegister()

    await user.type(screen.getByPlaceholderText('Username'), 'existing')
    await user.type(screen.getByPlaceholderText('Email'), 'test@example.com')
    await user.type(screen.getByPlaceholderText(/Password/i), 'password123')
    await user.click(screen.getByRole('button', { name: /Create Account/i }))

    await waitFor(() => {
      expect(screen.getByText(/Username already exists/i)).toBeInTheDocument()
    })
  })

  it('should enforce password minimum length', async () => {
    const user = userEvent.setup()
    renderRegister()

    const passwordInput = screen.getByPlaceholderText(/Password/i) as HTMLInputElement
    await user.type(passwordInput, 'short')

    expect(passwordInput.minLength).toBe(8)
  })

  it('should populate form fields correctly', async () => {
    const user = userEvent.setup()
    renderRegister()

    const usernameInput = screen.getByPlaceholderText('Username') as HTMLInputElement
    const emailInput = screen.getByPlaceholderText('Email') as HTMLInputElement
    const passwordInput = screen.getByPlaceholderText(/Password/i) as HTMLInputElement

    await user.type(usernameInput, 'testuser')
    await user.type(emailInput, 'test@example.com')
    await user.type(passwordInput, 'testpass123')

    expect(usernameInput.value).toBe('testuser')
    expect(emailInput.value).toBe('test@example.com')
    expect(passwordInput.value).toBe('testpass123')
  })

  it('should have login link', () => {
    renderRegister()
    expect(screen.getByText(/Already have an account/i)).toBeInTheDocument()
    expect(screen.getByRole('link', { name: /Sign in/i })).toBeInTheDocument()
  })
})
