import axios from 'axios'

// all requests go through the vite proxy at /api
const client = axios.create({
  baseURL: '/api',
})

// before every request, grab the token from storage and attach it
// this runs automatically so no route has to think about auth headers
client.interceptors.request.use((config) => {
  const token = localStorage.getItem('token')
  if (token) {
    config.headers.Authorization = `Bearer ${token}`
  }
  return config
})

// if any request gets a 401, the token is expired or invalid
// clear storage and bounce the user to login
client.interceptors.response.use(
  (response) => response,
  (error) => {
    if (error.response?.status === 401) {
      localStorage.removeItem('token')
      localStorage.removeItem('role')
      window.location.href = '/login'
    }
    return Promise.reject(error)
  }
)

export default client