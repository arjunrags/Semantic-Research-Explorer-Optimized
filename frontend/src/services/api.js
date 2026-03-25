import axios from 'axios'
import toast from 'react-hot-toast'

const BASE = import.meta.env.VITE_API_URL || ''

const api = axios.create({
  baseURL: `${BASE}/api`,
  timeout: 30000,
  headers: { 'Content-Type': 'application/json' },
})

api.interceptors.response.use(
  (res) => res,
  (err) => {
    const msg = err.response?.data?.detail || err.message || 'Request failed'
    if (err.response?.status !== 404) {
      toast.error(msg, { duration: 3000 })
    }
    return Promise.reject(err)
  }
)

// ─── Graph ────────────────────────────────────────────────────────────────────
export const fetchGraph = (limit = 100, edgeTypes = 'citation,similarity') =>
  api.get('/graph/', { params: { limit, edge_types: edgeTypes } }).then(r => r.data)

export const fetchNeighbors = (paperId) =>
  api.get(`/graph/neighbors/${paperId}`).then(r => r.data)

// ─── Search ───────────────────────────────────────────────────────────────────
export const searchPapers = (query, topK = 10, filters = null) =>
  api.post('/search/', { query, top_k: topK, filters }).then(r => r.data)

// ─── Papers ───────────────────────────────────────────────────────────────────
export const getPaper = (paperId) =>
  api.get(`/papers/${paperId}`).then(r => r.data)

export const listPapers = (limit = 50, offset = 0) =>
  api.get('/papers/', { params: { limit, offset } }).then(r => r.data)

export const ingestPapers = (query, limit = 10) =>
  api.post('/papers/ingest', { query, limit }).then(r => r.data)

// ─── Summaries ────────────────────────────────────────────────────────────────
export const getSummary = (paperId, userId = null) =>
  api.post('/summaries/', { paper_id: paperId, user_id: userId }).then(r => r.data)

export const comparePapers = (paperIds) =>
  api.post('/summaries/compare', paperIds).then(r => r.data)

export const generateLitReview = (paperIds) =>
  api.post('/summaries/literature-review', paperIds).then(r => r.data)

// ─── Gaps ─────────────────────────────────────────────────────────────────────
export const fetchGaps = () =>
  api.get('/gaps/').then(r => r.data)

export const triggerGapCompute = () =>
  api.post('/gaps/compute').then(r => r.data)

// ─── Memory ───────────────────────────────────────────────────────────────────
export const storeMemory = (content, paperId = null, tags = []) =>
  api.post('/memory/store', { content, paper_id: paperId, tags }).then(r => r.data)

export const searchMemory = (query, responseFormat = 'interpreted') =>
  api.post('/memory/search', { query, response_format: responseFormat }).then(r => r.data)

export const getMemoryStats = () =>
  api.get('/memory/stats').then(r => r.data)

// ─── Health ───────────────────────────────────────────────────────────────────
export const checkHealth = () =>
  axios.get(`${BASE}/health`).then(r => r.data)
