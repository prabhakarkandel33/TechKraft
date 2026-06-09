import { useState } from 'react'
import { useNavigate, Link } from 'react-router-dom'
import { register } from '../api/auth'

export default function RegisterPage() {
  const navigate = useNavigate()
  const [email, setEmail] = useState('')
  const [password, setPassword] = useState('')
  const [error, setError] = useState('')
  const [loading, setLoading] = useState(false)

  async function handleRegister(e) {
    e.preventDefault()
    setError('')
    setLoading(true)

    try {
      await register(email, password)
      // registration returns a token but we redirect to login
      // so the user goes through the normal login flow
      navigate('/login')
    } catch (err) {
      setError(err.response?.data?.detail || 'registration failed')
    } finally {
      setLoading(false)
    }
  }

  return (
    <div style={styles.container}>
      <div style={styles.card}>
        <h1 style={styles.title}>TechKraft</h1>
        <p style={styles.subtitle}>Create a reviewer account</p>

        {error && <div style={styles.error}>{error}</div>}

        <form onSubmit={handleRegister} style={styles.form}>
          <input
            style={styles.input}
            type="email"
            placeholder="Email"
            value={email}
            onChange={(e) => setEmail(e.target.value)}
            required
          />
          <input
            style={styles.input}
            type="password"
            placeholder="Password"
            value={password}
            onChange={(e) => setPassword(e.target.value)}
            required
          />
          <button style={styles.button} type="submit" disabled={loading}>
            {loading ? 'Creating account...' : 'Register'}
          </button>
        </form>

        <p style={styles.loginLink}>
          Already have an account?{' '}
          <Link to="/login" style={styles.link}>Sign in</Link>
        </p>

        <p style={styles.note}>
          Note: all registered accounts are reviewer accounts.
          Admin access is provisioned separately.
        </p>
      </div>
    </div>
  )
}

const styles = {
  container: {
    minHeight: '100vh', display: 'flex',
    alignItems: 'center', justifyContent: 'center',
    background: '#f5f5f5',
  },
  card: {
    background: '#fff', padding: '2rem',
    borderRadius: '8px', boxShadow: '0 2px 8px rgba(0,0,0,0.1)',
    width: '100%', maxWidth: '400px',
  },
  title: { margin: 0, fontSize: '1.5rem', color: '#1a1a1a' },
  subtitle: { color: '#666', marginBottom: '1.5rem' },
  error: {
    background: '#fee', border: '1px solid #fcc',
    borderRadius: '4px', padding: '0.75rem',
    marginBottom: '1rem', color: '#c00', fontSize: '0.9rem',
  },
  form: { display: 'flex', flexDirection: 'column', gap: '1rem' },
  input: {
    padding: '0.75rem', border: '1px solid #ddd',
    borderRadius: '4px', fontSize: '1rem',
  },
  button: {
    padding: '0.75rem', background: '#2563eb',
    color: '#fff', border: 'none',
    borderRadius: '4px', fontSize: '1rem', cursor: 'pointer',
  },
  loginLink: {
    textAlign: 'center', marginTop: '1rem',
    fontSize: '0.9rem', color: '#666',
  },
  link: { color: '#2563eb', textDecoration: 'none' },
  note: {
    marginTop: '1rem', fontSize: '0.75rem',
    color: '#999', textAlign: 'center',
    borderTop: '1px solid #f0f0f0', paddingTop: '1rem',
  },
}