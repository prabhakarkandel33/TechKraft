import { useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { login } from '../api/auth'
import { Link } from 'react-router-dom'


// decode the role out of the JWT payload without a library
// JWT is three base64 chunks separated by dots — middle chunk is the payload
function getRoleFromToken(token) {
  try {
    const payload = JSON.parse(atob(token.split('.')[1]))
    return payload.role
  } catch {
    return 'reviewer'
  }
}

export default function LoginPage() {
  const navigate = useNavigate()
  const [email, setEmail] = useState('')
  const [password, setPassword] = useState('')
  const [error, setError] = useState('')
  const [loading, setLoading] = useState(false)

  async function handleLogin(e) {
    e.preventDefault()
    setError('')
    setLoading(true)

    try {
      const res = await login(email, password)
      const token = res.data.access_token

      // store token and role so any component can check them
      localStorage.setItem('token', token)
      localStorage.setItem('role', getRoleFromToken(token))

      navigate('/candidates')
    } catch (err) {
      setError(err.response?.data?.detail || 'login failed')
    } finally {
      setLoading(false)
    }
  }

  return (
    <div style={styles.container}>
      <div style={styles.card}>
        <h1 style={styles.title}>TechKraft</h1>
        <p style={styles.subtitle}>Candidate Review Dashboard</p>

        {error && <div style={styles.error}>{error}</div>}

        <form onSubmit={handleLogin} style={styles.form}>
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
            {loading ? 'Signing in...' : 'Sign In'}
          </button>

                    <p style={{ textAlign: 'center', fontSize: '0.9rem', color: '#666' }}>
                    Don't have an account?{' '}
                        <Link to="/register" style={{ color: '#2563eb', textDecoration: 'none' }}>
                        Register
                        </Link>
                    </p>
        </form>
      </div>
    </div>
  )
}

const styles = {
  container: {
    minHeight: '100vh',
    display: 'flex',
    alignItems: 'center',
    justifyContent: 'center',
    background: '#f5f5f5',
  },
  card: {
    background: '#fff',
    padding: '2rem',
    borderRadius: '8px',
    boxShadow: '0 2px 8px rgba(0,0,0,0.1)',
    width: '100%',
    maxWidth: '400px',
  },
  title: { margin: 0, fontSize: '1.5rem', color: '#1a1a1a' },
  subtitle: { color: '#666', marginBottom: '1.5rem' },
  error: {
    background: '#fee',
    border: '1px solid #fcc',
    borderRadius: '4px',
    padding: '0.75rem',
    marginBottom: '1rem',
    color: '#c00',
    fontSize: '0.9rem',
  },
  form: { display: 'flex', flexDirection: 'column', gap: '1rem' },
  input: {
    padding: '0.75rem',
    border: '1px solid #ddd',
    borderRadius: '4px',
    fontSize: '1rem',
    outline: 'none',
  },
  button: {
    padding: '0.75rem',
    background: '#2563eb',
    color: '#fff',
    border: 'none',
    borderRadius: '4px',
    fontSize: '1rem',
    cursor: 'pointer',
  },
}