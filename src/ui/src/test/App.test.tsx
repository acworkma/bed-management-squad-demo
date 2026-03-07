/**
 * App smoke tests — verify the three-pane layout renders.
 *
 * These tests will fail until Viper's WI-005 (UI Shell) lands.
 * That's expected — the test framework itself is what matters here.
 */

import { describe, it, expect } from 'vitest'
import { render, screen } from '@testing-library/react'
import App from '../../App'

describe('App', () => {
  it('renders without crashing', () => {
    render(<App />)
  })

  it('shows the Ops Dashboard pane', () => {
    render(<App />)
    // Look for the Ops Dashboard header — exact text may vary
    expect(
      screen.getByText(/ops dashboard|bed board|patient flow/i)
    ).toBeInTheDocument()
  })

  it('shows the Agent Conversation pane', () => {
    render(<App />)
    expect(
      screen.getByText(/agent conversation|agent chat/i)
    ).toBeInTheDocument()
  })

  it('shows the Event Timeline pane', () => {
    render(<App />)
    expect(
      screen.getByText(/event timeline|events/i)
    ).toBeInTheDocument()
  })

  it('applies dark mode class', () => {
    const { container } = render(<App />)
    // Dark mode is the default per spec. Check for the class on html/body/root.
    const root = container.closest('.dark') ?? container.querySelector('.dark')
    expect(root).not.toBeNull()
  })
})
