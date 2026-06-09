import { useState, useEffect } from 'react'
import { useNavigate } from 'react-router-dom'
import { getCandidates } from '../api/candidates'

const STATUS_OPTIONS = ['', 'new', 'reviewed', 'hired', 'rejected']
const ROLE_OPTIONS = ['', 'Full Stack Engineer', 'Backend Engineer', 'Frontend Engineer', 'Data Engineer', 'ML Engineer', 'DevOps Engineer']

export default function CandidateListPage() {
  const navigate = useNavigate()
  const role = localStorage.getItem('role')

  const [candidates, setCandidates] = useState([])
  const [total, setTotal] = useState(0)
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState('')

  // filters live in state so changing them triggers a fresh fetch
  const [filters, setFilters] = useState({
    status: '',
    role_applied: '',
    skill: '',
    keyword: '',
    page: 1,
    page_size: 10,
  })

  useEffect(() => {
    fetchCandidates()
  }, [filters])

  async function fetchCandidates() {
    setLoading(true)
    setError('')
    try {
      const res = await getCandidates(filters)
      setCandidates(res.data.data)
      setTotal(res.data.total)
    } catch (err) {
      setError('failed to load candidates')
    } finally {
      setLoading(false)
    }
  }

  function handleFilterChange(key, value) {
    // reset to page 1 whenever a filter changes
    // otherwise you could be on page 3 of a filter that only has 1 page
    setFilters(prev => ({ ...prev, [key]: value, page: 1 }))
  }

  function handleLogout() {
    localStorage.removeItem('token')
    localStorage.removeItem('role')
    navigate('/login')
  }

  const totalPages = Math.ceil(total / filters.page_size)

  return (
    <div style={styles.container}>
      <div style={styles.header}>
        <div>
          <h1 style={styles.title}>Candidates</h1>
          <span style={styles.badge}>
            {role === 'admin' ? 'Admin' : 'Reviewer'}
          </span>
        </div>
        <button style={styles.logoutBtn} onClick={handleLogout}>
          Logout
        </button>
      </div>

      {/* filter controls — PDF requires status, role, skill, keyword */}
      <div style={styles.filters}>
        <select
          style={styles.select}
          value={filters.status}
          onChange={(e) => handleFilterChange('status', e.target.value)}
        >
          {STATUS_OPTIONS.map(s => (
            <option key={s} value={s}>{s || 'All Statuses'}</option>
          ))}
        </select>

        <select
          style={styles.select}
          value={filters.role_applied}
          onChange={(e) => handleFilterChange('role_applied', e.target.value)}
        >
          {ROLE_OPTIONS.map(r => (
            <option key={r} value={r}>{r || 'All Roles'}</option>
          ))}
        </select>

        <input
          style={styles.input}
          placeholder="Filter by skill (e.g. Python)"
          value={filters.skill}
          onChange={(e) => handleFilterChange('skill', e.target.value)}
        />

        <input
          style={styles.input}
          placeholder="Search by name or email"
          value={filters.keyword}
          onChange={(e) => handleFilterChange('keyword', e.target.value)}
        />
      </div>

      {error && <div style={styles.error}>{error}</div>}

      {loading ? (
        <div style={styles.loading}>Loading candidates...</div>
      ) : (
        <>
          <div style={styles.meta}>
            Showing {candidates.length} of {total} candidates
          </div>

          <div style={styles.list}>
            {candidates.length === 0 ? (
              <div style={styles.empty}>No candidates match your filters.</div>
            ) : (
              candidates.map(candidate => (
                <div
                  key={candidate.id}
                  style={styles.card}
                  onClick={() => navigate(`/candidates/${candidate.id}`)}
                >
                  <div style={styles.cardTop}>
                    <div>
                      <div style={styles.name}>{candidate.name}</div>
                      <div style={styles.email}>{candidate.email}</div>
                    </div>
                    <span style={{
                      ...styles.statusBadge,
                      background: STATUS_COLORS[candidate.status] || '#ddd'
                    }}>
                      {candidate.status}
                    </span>
                  </div>

                  <div style={styles.cardBottom}>
                    <span style={styles.roleText}>{candidate.role_applied}</span>
                    <div style={styles.skills}>
                      {candidate.skills.map(skill => (
                        <span key={skill} style={styles.skillTag}>{skill}</span>
                      ))}
                    </div>
                  </div>

                  {/* admin sees internal notes inline on the list */}
                  {role === 'admin' && candidate.internal_notes && (
                    <div style={styles.notes}>
                      📝 {candidate.internal_notes}
                    </div>
                  )}
                </div>
              ))
            )}
          </div>

          {/* pagination controls */}
          {totalPages > 1 && (
            <div style={styles.pagination}>
              <button
                style={styles.pageBtn}
                disabled={filters.page === 1}
                onClick={() => setFilters(prev => ({ ...prev, page: prev.page - 1 }))}
              >
                Previous
              </button>
              <span style={styles.pageInfo}>
                Page {filters.page} of {totalPages}
              </span>
              <button
                style={styles.pageBtn}
                disabled={filters.page >= totalPages}
                onClick={() => setFilters(prev => ({ ...prev, page: prev.page + 1 }))}
              >
                Next
              </button>
            </div>
          )}
        </>
      )}
    </div>
  )
}

const STATUS_COLORS = {
  new: '#dbeafe',
  reviewed: '#fef9c3',
  hired: '#dcfce7',
  rejected: '#fee2e2',
  archived: '#f3f4f6',
}

const styles = {
  container: { maxWidth: '900px', margin: '0 auto', padding: '2rem' },
  header: {
    display: 'flex', justifyContent: 'space-between',
    alignItems: 'flex-start', marginBottom: '1.5rem'
  },
  title: { margin: 0, fontSize: '1.5rem' },
  badge: {
    display: 'inline-block', fontSize: '0.75rem',
    background: '#e0e7ff', color: '#3730a3',
    padding: '2px 8px', borderRadius: '999px', marginTop: '4px'
  },
  logoutBtn: {
    padding: '0.5rem 1rem', background: '#fee2e2',
    color: '#b91c1c', border: 'none', borderRadius: '4px', cursor: 'pointer'
  },
  filters: {
    display: 'flex', gap: '0.75rem',
    flexWrap: 'wrap', marginBottom: '1rem'
  },
  select: {
    padding: '0.5rem', border: '1px solid #ddd',
    borderRadius: '4px', fontSize: '0.9rem', background: '#fff'
  },
  input: {
    padding: '0.5rem', border: '1px solid #ddd',
    borderRadius: '4px', fontSize: '0.9rem', minWidth: '200px'
  },
  error: {
    background: '#fee', border: '1px solid #fcc',
    padding: '0.75rem', borderRadius: '4px',
    color: '#c00', marginBottom: '1rem'
  },
  loading: { textAlign: 'center', padding: '2rem', color: '#666' },
  meta: { color: '#666', fontSize: '0.85rem', marginBottom: '0.75rem' },
  list: { display: 'flex', flexDirection: 'column', gap: '0.75rem' },
  empty: { textAlign: 'center', padding: '2rem', color: '#999' },
  card: {
    background: '#fff', border: '1px solid #e5e7eb',
    borderRadius: '8px', padding: '1rem',
    cursor: 'pointer', transition: 'box-shadow 0.15s',
  },
  cardTop: {
    display: 'flex', justifyContent: 'space-between',
    alignItems: 'flex-start', marginBottom: '0.5rem'
  },
  name: { fontWeight: '600', fontSize: '1rem' },
  email: { color: '#666', fontSize: '0.85rem' },
  statusBadge: {
    fontSize: '0.75rem', padding: '2px 10px',
    borderRadius: '999px', fontWeight: '500'
  },
  cardBottom: {
    display: 'flex', alignItems: 'center',
    gap: '1rem', flexWrap: 'wrap'
  },
  roleText: { color: '#555', fontSize: '0.85rem' },
  skills: { display: 'flex', gap: '0.4rem', flexWrap: 'wrap' },
  skillTag: {
    background: '#f3f4f6', fontSize: '0.75rem',
    padding: '2px 8px', borderRadius: '4px', color: '#374151'
  },
  notes: {
    marginTop: '0.5rem', fontSize: '0.8rem',
    color: '#555', background: '#fafafa',
    padding: '0.4rem 0.6rem', borderRadius: '4px'
  },
  pagination: {
    display: 'flex', alignItems: 'center',
    justifyContent: 'center', gap: '1rem', marginTop: '1.5rem'
  },
  pageBtn: {
    padding: '0.5rem 1rem', border: '1px solid #ddd',
    borderRadius: '4px', cursor: 'pointer', background: '#fff'
  },
  pageInfo: { color: '#555', fontSize: '0.9rem' },
}