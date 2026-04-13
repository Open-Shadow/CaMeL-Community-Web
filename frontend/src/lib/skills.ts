import { api } from '@/hooks/use-auth'

export interface SkillSummary {
  id: number
  name: string
  slug: string
  description: string
  category: string
  tags: string[]
  pricing_model: 'FREE' | 'PAID'
  price: number | null
  status: 'DRAFT' | 'SCANNING' | 'APPROVED' | 'REJECTED' | 'ARCHIVED'
  is_featured: boolean
  current_version: string
  total_calls: number
  avg_rating: number
  review_count: number
  rejection_reason: string
  readme_html: string
  package_size: number
  download_count: number
  creator_id: number
  creator_name: string
  created_at: string
  updated_at: string
  has_purchased: boolean
}

export interface SkillCallResult {
  output_text: string
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
  version: string
  changelog: string
  status: string
  created_at: string
}

export interface TrendingSkill {
  id: number
  name: string
  slug: string
  description: string
  category: string
  pricing_model: 'FREE' | 'PAID'
  price: number | null
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
  locked_version: string | null
  auto_follow_latest: boolean
}

export interface SkillListParams {
  category?: string
  q?: string
  sort?: 'latest' | 'rating' | 'calls' | 'featured'
  page?: number
  page_size?: number
}

export interface SkillCreatePayload {
  name: string
  description: string
  category: string
  tags: string[]
  pricing_model: 'FREE' | 'PAID'
  price?: number | null
  changelog?: string
  package_file: File
}

export interface SkillUpdatePayload {
  name?: string
  description?: string
  category?: string
  tags?: string[]
  pricing_model?: 'FREE' | 'PAID'
  price?: number | null
  changelog?: string
  package_file?: File
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

export async function createSkill(payload: SkillCreatePayload) {
  const formData = new FormData()
  formData.append('package', payload.package_file)
  formData.append('name', payload.name)
  formData.append('description', payload.description)
  formData.append('category', payload.category)
  formData.append('tags', JSON.stringify(payload.tags))
  formData.append('pricing_model', payload.pricing_model)
  if (payload.price != null) formData.append('price', String(payload.price))
  if (payload.changelog) formData.append('changelog', payload.changelog)
  const response = await api.post<SkillSummary>('/skills/', formData, {
    headers: { 'Content-Type': 'multipart/form-data' },
  })
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
  payload: { locked_version: string | null; auto_follow_latest: boolean },
) {
  const response = await api.post<SkillUsagePreference>(`/skills/${skillId}/usage-preference`, payload)
  return response.data
}

export async function updateSkill(skillId: number, payload: SkillUpdatePayload) {
  const formData = new FormData()
  if (payload.package_file) formData.append('package', payload.package_file)
  if (payload.name != null) formData.append('name', payload.name)
  if (payload.description != null) formData.append('description', payload.description)
  if (payload.category != null) formData.append('category', payload.category)
  if (payload.tags != null) formData.append('tags', JSON.stringify(payload.tags))
  if (payload.pricing_model != null) formData.append('pricing_model', payload.pricing_model)
  if (payload.price != null) formData.append('price', String(payload.price))
  if (payload.changelog) formData.append('changelog', payload.changelog)
  const response = await api.patch<SkillSummary>(`/skills/${skillId}`, formData, {
    headers: { 'Content-Type': 'multipart/form-data' },
  })
  return response.data
}

export interface SkillPurchaseResult {
  id: number
  skill_id: number
  paid_amount: number
  payment_type: string
  created_at: string
}

export interface SkillPurchaseDetail {
  id: number
  name: string
  slug: string
  description: string
  category: string
  tags: string[]
  pricing_model: 'FREE' | 'PAID'
  price: number | null
  status: string
  is_featured: boolean
  current_version: string
  total_calls: number
  avg_rating: number
  review_count: number
  rejection_reason: string
  readme_html: string
  package_size: number
  download_count: number
  creator_id: number
  creator_name: string
  created_at: string
  updated_at: string
  purchase_id: number
  paid_amount: number
  payment_type: string
  purchased_at: string
}

export interface SkillReportResult {
  id: number
  skill_id: number
  reason: string
  detail: string
  created_at: string
}

export async function purchaseSkill(skillId: number) {
  const response = await api.post<SkillPurchaseResult>(`/skills/${skillId}/purchase`)
  return response.data
}

export async function downloadSkill(skillId: number, version?: string) {
  // Backend returns a JSON body with the pre-signed download URL.
  const params: Record<string, string> = {}
  if (version) params.version = version
  const response = await api.get<{ url: string }>(`/skills/${skillId}/download`, { params })
  if (response.data.url) {
    window.open(response.data.url, '_blank')
  }
}

export async function listPurchasedSkills() {
  const response = await api.get<SkillPurchaseDetail[]>('/skills/purchased')
  return response.data
}

export async function reportSkill(skillId: number, payload: { reason: string; detail?: string }) {
  const response = await api.post<SkillReportResult>(`/skills/${skillId}/report`, payload)
  return response.data
}

export interface PackageFileEntry {
  path: string
  size: number
  is_dir: boolean
}

export async function getSkillFileTree(skillId: number) {
  const response = await api.get<PackageFileEntry[]>(`/skills/${skillId}/file-tree`)
  return response.data
}
