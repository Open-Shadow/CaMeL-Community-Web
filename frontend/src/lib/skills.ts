import { api } from '@/hooks/use-auth'

export interface SkillSummary {
  id: number
  name: string
  slug: string
  description: string
  system_prompt: string
  user_prompt_template: string
  output_format: string
  example_input: string
  example_output: string
  category: string
  tags: string[]
  pricing_model: 'FREE' | 'PER_USE'
  price_per_use: number | null
  status: 'DRAFT' | 'PENDING_REVIEW' | 'APPROVED' | 'REJECTED' | 'ARCHIVED'
  is_featured: boolean
  current_version: number
  total_calls: number
  avg_rating: number
  review_count: number
  rejection_reason: string
  creator_id: number
  creator_name: string
  created_at: string
  updated_at: string
}

export interface SkillCallResult {
  output_text: string
  amount_charged: number
  duration_ms: number | null
}

export interface SkillSearchResult {
  items: SkillSummary[]
  source: string
  total: number
  experiment_bucket?: string
}

export interface SkillReview {
  id: number
  rating: number
  comment: string
  tags: string[]
  reviewer_id: number
  reviewer_name: string
  created_at: string
}

export interface SkillVersion {
  id: number
  version: number
  system_prompt: string
  user_prompt_template: string
  change_note: string
  is_major: boolean
  created_at: string
}

export interface TrendingSkill {
  id: number
  name: string
  slug: string
  description: string
  category: string
  pricing_model: 'FREE' | 'PER_USE'
  price_per_use: number | null
  total_calls: number
  avg_rating: number
  review_count: number
  creator_name: string
}

export interface RecommendedSkill extends TrendingSkill {
  recommendation_reason: string
}

export interface SkillIncomeDashboard {
  total_income: number
  total_calls: number
  skills: Array<{
    skill_id: number
    skill_name: string
    calls: number
    income: number
    avg_rating: number
    review_count: number
  }>
}

export interface SkillUsagePreference {
  skill_id: number
  locked_version: number | null
  auto_follow_latest: boolean
}

export interface SkillListParams {
  category?: string
  q?: string
  sort?: 'latest' | 'rating' | 'calls' | 'featured'
  page?: number
  page_size?: number
}

export interface SkillPayload {
  name: string
  description: string
  system_prompt: string
  user_prompt_template?: string
  output_format?: string
  example_input?: string
  example_output?: string
  category: string
  tags: string[]
  pricing_model: 'FREE' | 'PER_USE'
  price_per_use?: number | null
}

export async function listSkills(params: SkillListParams = {}) {
  const response = await api.get<SkillSummary[]>('/skills/', { params })
  return response.data
}

export async function searchSkills(params: Pick<SkillListParams, 'q' | 'category'> & { limit?: number }) {
  const response = await api.get<SkillSearchResult>('/search/skills', { params })
  return response.data
}

export async function getSkill(skillId: number) {
  const response = await api.get<SkillSummary>(`/skills/${skillId}`)
  return response.data
}

export async function getMySkills() {
  const response = await api.get<SkillSummary[]>('/skills/mine')
  return response.data
}

export async function createSkill(payload: SkillPayload) {
  const response = await api.post<SkillSummary>('/skills/', payload)
  return response.data
}

export async function submitSkill(skillId: number) {
  const response = await api.post<SkillSummary>(`/skills/${skillId}/submit`)
  return response.data
}

export async function archiveSkill(skillId: number) {
  const response = await api.post<SkillSummary>(`/skills/${skillId}/archive`)
  return response.data
}

export async function restoreSkill(skillId: number) {
  const response = await api.post<SkillSummary>(`/skills/${skillId}/restore`)
  return response.data
}

export async function deleteSkill(skillId: number) {
  const response = await api.delete<{ message: string }>(`/skills/${skillId}`)
  return response.data
}

export async function callSkill(skillId: number, inputText: string) {
  const response = await api.post<SkillCallResult>(`/skills/${skillId}/call`, {
    input_text: inputText,
  })
  return response.data
}

export async function listSkillReviews(skillId: number) {
  const response = await api.get<SkillReview[]>(`/skills/${skillId}/reviews`)
  return response.data
}

export async function addSkillReview(
  skillId: number,
  payload: { rating: number; comment: string; tags: string[] },
) {
  const response = await api.post<SkillReview>(`/skills/${skillId}/reviews`, payload)
  return response.data
}

export async function listSkillVersions(skillId: number) {
  const response = await api.get<SkillVersion[]>(`/skills/${skillId}/versions`)
  return response.data
}

export async function listTrendingSkills(limit = 8) {
  const response = await api.get<TrendingSkill[]>('/skills/trending/list', { params: { limit } })
  return response.data
}

export async function listRecommendedSkills(limit = 8) {
  const response = await api.get<RecommendedSkill[]>('/skills/recommended', { params: { limit } })
  return response.data
}

export async function getSkillIncomeDashboard() {
  const response = await api.get<SkillIncomeDashboard>('/payments/skills/income')
  return response.data
}

export async function getSkillUsagePreference(skillId: number) {
  const response = await api.get<SkillUsagePreference>(`/skills/${skillId}/usage-preference`)
  return response.data
}

export async function updateSkillUsagePreference(
  skillId: number,
  payload: { locked_version: number | null; auto_follow_latest: boolean },
) {
  const response = await api.post<SkillUsagePreference>(`/skills/${skillId}/usage-preference`, payload)
  return response.data
}
