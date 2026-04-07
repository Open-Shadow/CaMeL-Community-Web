import { api } from '@/hooks/use-auth'

export interface BountyUser {
  id: number
  username: string
  display_name: string
  level: string
  credit_score: number
}

export interface BountyApplication {
  id: number
  proposal: string
  estimated_days: number
  applicant: BountyUser
  created_at: string
}

export interface BountyDeliverable {
  id: number
  content: string
  attachments: string[]
  revision_number: number
  submitter: BountyUser
  created_at: string
}

export interface BountyComment {
  id: number
  content: string
  author: BountyUser
  created_at: string
}

export interface ArbitrationVote {
  id: number
  arbitrator: BountyUser
  vote: 'HUNTER_WIN' | 'CREATOR_WIN' | 'PARTIAL'
  hunter_ratio: number | null
  created_at: string
}

export interface ArbitrationCase {
  id: number
  creator_statement: string
  hunter_statement: string
  result: string
  hunter_ratio: number | null
  appeal_by_id: number | null
  appeal_fee_paid: boolean
  admin_final_result: string
  deadline: string | null
  resolved_at: string | null
  arbitrators: BountyUser[]
  votes: ArbitrationVote[]
}

export interface BountyReview {
  id: number
  reviewer: BountyUser
  reviewee: BountyUser
  quality_rating: number
  communication_rating: number
  responsiveness_rating: number
  comment: string
  created_at: string
}

export interface BountySummary {
  id: number
  title: string
  description: string
  bounty_type: string
  reward: number
  status: string
  deadline: string
  revision_count: number
  is_cold: boolean
  application_count: number
  creator: BountyUser
  accepted_applicant: BountyUser | null
  created_at: string
  updated_at: string
}

export interface BountyDetail extends BountySummary {
  applications: BountyApplication[]
  deliverables: BountyDeliverable[]
  comments: BountyComment[]
  reviews: BountyReview[]
  arbitration: ArbitrationCase | null
}

export interface BountyListResponse {
  items: BountySummary[]
  total: number
  limit: number
  offset: number
}

export async function listBounties(params: Record<string, string | number | undefined> = {}) {
  const response = await api.get<BountyListResponse>('/bounties/', { params })
  return response.data
}

export async function listMyBounties(role: 'all' | 'creator' | 'hunter' = 'all') {
  const response = await api.get<BountyListResponse>('/bounties/mine', { params: { role } })
  return response.data
}

export async function getBounty(id: number) {
  const response = await api.get<BountyDetail>(`/bounties/${id}`)
  return response.data
}

export async function createBounty(payload: {
  title: string
  description: string
  bounty_type: string
  reward: number
  deadline: string
}) {
  const response = await api.post<BountyDetail>('/bounties/', payload)
  return response.data
}

export async function applyBounty(id: number, payload: { proposal: string; estimated_days: number }) {
  return api.post(`/bounties/${id}/apply`, payload)
}

export async function acceptBountyApplication(id: number, applicationId: number) {
  const response = await api.post<BountyDetail>(`/bounties/${id}/accept/${applicationId}`)
  return response.data
}

export async function addBountyComment(id: number, content: string) {
  return api.post(`/bounties/${id}/comments`, { content })
}

export async function submitBountyDelivery(id: number, payload: { content: string; attachments?: string[] }) {
  const response = await api.post<BountyDetail>(`/bounties/${id}/submit`, payload)
  return response.data
}

export async function approveBounty(id: number) {
  const response = await api.post<BountyDetail>(`/bounties/${id}/approve`)
  return response.data
}

export async function requestBountyRevision(id: number, feedback: string) {
  const response = await api.post<BountyDetail>(`/bounties/${id}/revision`, { feedback })
  return response.data
}

export async function cancelBounty(id: number, feedback = '') {
  const response = await api.post<BountyDetail>(`/bounties/${id}/cancel`, { feedback })
  return response.data
}

export async function createBountyDispute(id: number, content: string) {
  const response = await api.post<BountyDetail>(`/bounties/${id}/dispute`, { content })
  return response.data
}

export async function submitArbitrationStatement(id: number, content: string) {
  const response = await api.post<BountyDetail>(`/bounties/${id}/arbitration/statement`, { content })
  return response.data
}

export async function startArbitration(id: number) {
  const response = await api.post<BountyDetail>(`/bounties/${id}/arbitration/start`)
  return response.data
}

export async function castArbitrationVote(
  id: number,
  payload: { vote: 'HUNTER_WIN' | 'CREATOR_WIN' | 'PARTIAL'; hunter_ratio?: number | null },
) {
  const response = await api.post<BountyDetail>(`/bounties/${id}/arbitration/vote`, payload)
  return response.data
}

export async function appealArbitration(id: number, reason: string) {
  const response = await api.post<BountyDetail>(`/bounties/${id}/arbitration/appeal`, { reason })
  return response.data
}

export async function addBountyReview(
  id: number,
  payload: {
    quality_rating: number
    communication_rating: number
    responsiveness_rating: number
    comment: string
  },
) {
  const response = await api.post<BountyDetail>(`/bounties/${id}/reviews`, payload)
  return response.data
}

export async function listActiveDisputes() {
  const response = await api.get<Array<{
    id: number
    title: string
    status: string
    creator: BountyUser
    accepted_applicant: BountyUser | null
    arbitration: ArbitrationCase | null
  }>>('/bounties/admin/arbitrations')
  return response.data
}
