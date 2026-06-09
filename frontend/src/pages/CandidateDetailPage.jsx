import { useState, useEffect } from 'react'
import { useParams, useNavigate } from 'react-router-dom'
import { getCandidate, submitScore, triggerSummary, updateNotes } from '../api/candidates'

const CATEGORIES = ['technical', 'communication', 'problem solving', 'culture fit', 'experience']

export default function CandidateDetailPage() {
  const { id } = useParams()
  const navigate = useNavigate()
  const role = localStorage.getItem('role')

  const [candidate, setCandidate] = useState(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState('')

  // scoring form state
  const [scoreForm, setScoreForm] = useState({ category: 'technical', score: 3, note: '' })
  const [scoreLoading, setScoreLoading] = useState(false)
  const [scoreSuccess, setScoreSuccess] = useState('')
  const [scoreError, setScoreError] = useState('')

  // AI summary state — PDF requires loading + error states
  const [summary, setSummary] = useState('')
  const [summaryLoading, setSummaryLoading] = useState(false)
  const [summaryError, setSummaryError] = useState('')

  // admin notes state
  const [notes, setNotes] = useState('')
  const [notesLoading, setNotesLoading] = useState(false)
  const [notesSuccess, setNotesSuccess] = useState('')

  useEffect(() => {
    fetchCandidate()
  }, [id])

  async function fetchCandidate() {
    setLoading(true)
    try {
      const res = await getCandidate(id)
      setCandidate(res.data)
      setNotes(res.data.internal_notes || '')
    } catch {
      setError('candidate not found')
    } finally {
      setLoading(false)
    }
  }

  async function handleScoreSubmit(e) {
    e.preventDefault()
    setScoreLoading(true)
    setScoreError('')
    setScoreSuccess('')

    try {
      await submitScore(id, {
        category: scoreForm.category,
        score: parseInt(scoreForm.score),
        note: scoreForm.note || undefined,
      })
      setScoreSuccess('score submitted successfully')
      // refresh so the new score appears in the list immediately
      await fetchCandidate()
    } catch (err) {
      setScoreError(err.response?.data?.detail || 'failed to submit score')
    } finally {
      setScoreLoading(false)
    }
  }

  async function handleSummary() {
    setSummaryLoading(true)
    setSummaryError('')
    setSummary('')

    try {
      // this awaits the 2s mock delay on the backend
      // the loading spinner runs the whole time — PDF checks for this
      const res = await triggerSummary(id)
      setSummary(res.data.summary)
    } catch {
      setSummaryError('failed to generate summary, please try again')
    } finally {
      setSummaryLoading(false)
    }
  }

  async function handleNotesUpdate(e) {
    e.preventDefault()
    setNotesLoading(true)
    setNotesSuccess('')

    try {
      await updateNotes(id, notes)
      setNotesSuccess('notes saved')
    } catch {
      // silently fail — admin will see no confirmation
    } finally {
      setNotesLoading(false)
    }
  }

  if (loading) return <div style={styles.centered}>Loading candidate...</div>
  if (error) return <div style={styles.centered}>{error}</div>
  if (!candidate) return null

  return (
    <div style={styles.container}>
      <button style={styles.backBtn} onClick={() => navigate('/candidates')}>
        ← Back to list
      </button>

      {/* profile section */}
      <div style={styles.card}>
        <div style={styles.profileTop}>
          <div>
            <h2 style={styles.name}>{candidate.name}</h2>
            <div style={styles.email}>{candidate.email}</div>
            <div style={styles.role}>{candidate.role_applied}</div>
          </div>
          <span style={{
            ...styles.statusBadge,
            background: STATUS_COLORS[candidate.status] || '#ddd'
          }}>
            {candidate.status}
          </span>
        </div>

        <div style={styles.skills}>
          {candidate.skills.map(skill => (
            <span key={skill} style={styles.skillTag}>{skill}</span>
          ))}
        </div>
      </div>

      {/* scores section */}
      <div style={styles.card}>
        <h3 style={styles.sectionTitle}>
          {role === 'admin' ? 'All Scores' : 'Your Scores'}
        </h3>

        {candidate.scores.length === 0 ? (
          <p style={styles.empty}>
            {role === 'admin' ? 'No scores submitted yet.' : 'You have not scored this candidate yet.'}
          </p>
        ) : (
          <table style={styles.table}>
            <thead>
              <tr>
                <th style={styles.th}>Category</th>
                <th style={styles.th}>Score</th>
                <th style={styles.th}>Note</th>
                <th style={styles.th}>Date</th>
              </tr>
            </thead>
            <tbody>
              {candidate.scores.map(score => (
                <tr key={score.id}>
                  <td style={styles.td}>{score.category}</td>
                  <td style={styles.td}>
                    <span style={styles.scorePill}>{score.score}/5</span>
                  </td>
                  <td style={styles.td}>{score.note || '—'}</td>
                  <td style={styles.td}>
                    {new Date(score.created_at).toLocaleDateString()}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        )}
      </div>

      {/* scoring form */}
      <div style={styles.card}>
        <h3 style={styles.sectionTitle}>Submit a Score</h3>

        {scoreSuccess && <div style={styles.success}>{scoreSuccess}</div>}
        {scoreError && <div style={styles.error}>{scoreError}</div>}

        <form onSubmit={handleScoreSubmit} style={styles.form}>
          <div style={styles.formRow}>
            <div style={styles.formGroup}>
              <label style={styles.label}>Category</label>
              <select
                style={styles.select}
                value={scoreForm.category}
                onChange={(e) => setScoreForm(prev => ({ ...prev, category: e.target.value }))}
              >
                {CATEGORIES.map(c => (
                  <option key={c} value={c}>{c}</option>
                ))}
              </select>
            </div>

            <div style={styles.formGroup}>
              <label style={styles.label}>Score (1-5)</label>
              <select
                style={styles.select}
                value={scoreForm.score}
                onChange={(e) => setScoreForm(prev => ({ ...prev, score: e.target.value }))}
              >
                {[1, 2, 3, 4, 5].map(n => (
                  <option key={n} value={n}>{n}</option>
                ))}
              </select>
            </div>
          </div>

          <div style={styles.formGroup}>
            <label style={styles.label}>Note (optional)</label>
            <textarea
              style={styles.textarea}
              placeholder="Add a note about this score..."
              value={scoreForm.note}
              onChange={(e) => setScoreForm(prev => ({ ...prev, note: e.target.value }))}
              rows={3}
            />
          </div>

          <button style={styles.primaryBtn} type="submit" disabled={scoreLoading}>
            {scoreLoading ? 'Submitting...' : 'Submit Score'}
          </button>
        </form>
      </div>

      {/* AI summary section — PDF requires loading + error states */}
      <div style={styles.card}>
        <h3 style={styles.sectionTitle}>AI Summary</h3>

        {!summary && !summaryLoading && !summaryError && (
          <p style={styles.empty}>
            No summary generated yet. Click below to generate one.
          </p>
        )}

        {summaryLoading && (
          <div style={styles.summaryLoading}>
            <div style={styles.spinner} />
            <span>Generating summary, please wait...</span>
          </div>
        )}

        {summaryError && (
          <div style={styles.error}>{summaryError}</div>
        )}

        {summary && (
          <div style={styles.summaryBox}>
            {summary}
          </div>
        )}

        <button
          style={styles.secondaryBtn}
          onClick={handleSummary}
          disabled={summaryLoading}
        >
          {summaryLoading ? 'Generating...' : summary ? 'Regenerate Summary' : 'Generate AI Summary'}
        </button>
      </div>

      {/* admin only internal notes panel */}
      {role === 'admin' && (
        <div style={{ ...styles.card, borderLeft: '4px solid #2563eb' }}>
          <h3 style={styles.sectionTitle}>Internal Notes (Admin Only)</h3>
          <p style={styles.adminNote}>
            These notes are only visible to admins and never exposed to reviewers.
          </p>

          {notesSuccess && <div style={styles.success}>{notesSuccess}</div>}

          <form onSubmit={handleNotesUpdate} style={styles.form}>
            <textarea
              style={styles.textarea}
              placeholder="Add internal notes about this candidate..."
              value={notes}
              onChange={(e) => setNotes(e.target.value)}
              rows={4}
            />
            <button style={styles.primaryBtn} type="submit" disabled={notesLoading}>
              {notesLoading ? 'Saving...' : 'Save Notes'}
            </button>
          </form>
        </div>
      )}
    </div>
  )
}

const STATUS_COLORS = {
  new: '#dbeafe',
  reviewed: '#fef9c3',
  hired: '#dcfce7',
  rejected: '#fee2e2',
}

const styles = {
  container: { maxWidth: '800px', margin: '0 auto', padding: '2rem' },
  centered: { textAlign: 'center', padding: '4rem', color: '#666' },
  backBtn: {
    background: 'none', border: 'none', color: '#2563eb',
    cursor: 'pointer', fontSize: '0.9rem', marginBottom: '1rem',
    padding: 0,
  },
  card: {
    background: '#fff', border: '1px solid #e5e7eb',
    borderRadius: '8px', padding: '1.5rem', marginBottom: '1rem',
  },
  profileTop: {
    display: 'flex', justifyContent: 'space-between',
    alignItems: 'flex-start', marginBottom: '1rem'
  },
  name: { margin: 0, fontSize: '1.4rem' },
  email: { color: '#666', fontSize: '0.9rem', marginTop: '4px' },
  role: { color: '#2563eb', fontSize: '0.9rem', marginTop: '4px' },
  statusBadge: {
    fontSize: '0.8rem', padding: '4px 12px',
    borderRadius: '999px', fontWeight: '500'
  },
  skills: { display: 'flex', gap: '0.5rem', flexWrap: 'wrap' },
  skillTag: {
    background: '#f3f4f6', fontSize: '0.8rem',
    padding: '3px 10px', borderRadius: '4px', color: '#374151'
  },
  sectionTitle: { margin: '0 0 1rem', fontSize: '1rem', fontWeight: '600' },
  empty: { color: '#999', fontSize: '0.9rem' },
  table: { width: '100%', borderCollapse: 'collapse' },
  th: {
    textAlign: 'left', padding: '0.5rem',
    borderBottom: '2px solid #e5e7eb',
    fontSize: '0.8rem', color: '#666'
  },
  td: {
    padding: '0.5rem', borderBottom: '1px solid #f3f4f6',
    fontSize: '0.9rem'
  },
  scorePill: {
    background: '#dbeafe', color: '#1e40af',
    padding: '2px 8px', borderRadius: '999px', fontSize: '0.8rem'
  },
  form: { display: 'flex', flexDirection: 'column', gap: '1rem' },
  formRow: { display: 'flex', gap: '1rem' },
  formGroup: { display: 'flex', flexDirection: 'column', gap: '0.4rem', flex: 1 },
  label: { fontSize: '0.85rem', color: '#555', fontWeight: '500' },
  select: {
    padding: '0.5rem', border: '1px solid #ddd',
    borderRadius: '4px', fontSize: '0.9rem'
  },
  textarea: {
    padding: '0.75rem', border: '1px solid #ddd',
    borderRadius: '4px', fontSize: '0.9rem',
    resize: 'vertical', fontFamily: 'inherit'
  },
  primaryBtn: {
    padding: '0.75rem 1.5rem', background: '#2563eb',
    color: '#fff', border: 'none', borderRadius: '4px',
    fontSize: '0.9rem', cursor: 'pointer', alignSelf: 'flex-start'
  },
  secondaryBtn: {
    marginTop: '1rem', padding: '0.6rem 1.2rem',
    background: '#f3f4f6', color: '#374151',
    border: '1px solid #ddd', borderRadius: '4px',
    fontSize: '0.9rem', cursor: 'pointer'
  },
  summaryLoading: {
    display: 'flex', alignItems: 'center', gap: '0.75rem',
    color: '#555', padding: '1rem 0'
  },
  spinner: {
    width: '18px', height: '18px',
    border: '2px solid #ddd',
    borderTop: '2px solid #2563eb',
    borderRadius: '50%',
    animation: 'spin 0.8s linear infinite'
  },
  summaryBox: {
    background: '#f8fafc', border: '1px solid #e2e8f0',
    borderRadius: '6px', padding: '1rem',
    fontSize: '0.9rem', lineHeight: '1.6',
    color: '#334155', marginBottom: '0.5rem'
  },
  success: {
    background: '#dcfce7', border: '1px solid #bbf7d0',
    padding: '0.75rem', borderRadius: '4px',
    color: '#166534', fontSize: '0.9rem', marginBottom: '0.5rem'
  },
  error: {
    background: '#fee', border: '1px solid #fcc',
    padding: '0.75rem', borderRadius: '4px',
    color: '#c00', fontSize: '0.9rem', marginBottom: '0.5rem'
  },
  adminNote: { fontSize: '0.8rem', color: '#888', marginBottom: '0.75rem' },
}