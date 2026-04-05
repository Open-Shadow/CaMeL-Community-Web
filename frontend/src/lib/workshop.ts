import { api } from '@/hooks/use-auth'

export interface ArticleAuthor {
  id: number
  username: string
  display_name: string
  level: string
  credit_score: number
}

export interface RelatedSkillSummary {
  id: number
  name: string
  category: string
  pricing_model: 'FREE' | 'PER_USE'
  price_per_use: number | null
  total_calls: number
  avg_rating: number
  creator_name: string
}

export interface ArticleSummary {
  id: number
  title: string
  slug: string
  excerpt: string
  difficulty: 'BEGINNER' | 'INTERMEDIATE' | 'ADVANCED'
  article_type: 'TUTORIAL' | 'CASE_STUDY' | 'PITFALL' | 'REVIEW' | 'DISCUSSION'
  model_tags: string[]
  custom_tags: string[]
  status: 'DRAFT' | 'PUBLISHED' | 'ARCHIVED'
  is_featured: boolean
  net_votes: number
  total_tips: number
  comment_count: number
  view_count: number
  author: ArticleAuthor
  related_skill: RelatedSkillSummary | null
  created_at: string
  updated_at: string
  published_at: string | null
}

export interface ArticleDetail extends ArticleSummary {
  content: string
  is_outdated: boolean
  my_vote: 'UP' | 'DOWN' | null
}

export interface RecommendedArticle extends ArticleSummary {
  recommendation_reason: string
}

export interface ArticleCommentReply {
  id: number
  content: string
  net_votes: number
  is_pinned: boolean
  is_collapsed: boolean
  my_vote: 'UP' | 'DOWN' | null
  author: ArticleAuthor
  created_at: string
  updated_at: string
}

export interface ArticleComment extends ArticleCommentReply {
  replies: ArticleCommentReply[]
}

export interface ArticleSearchResult {
  items: ArticleSummary[]
  source: string
  total: number
  experiment_bucket?: string
}

export interface SeriesSummary {
  id: number
  title: string
  description: string
  cover_url: string
  is_completed: boolean
  completion_rewarded: boolean
  article_count: number
  published_count: number
  author: ArticleAuthor
  created_at: string
  updated_at: string
}

export interface SeriesDetail extends SeriesSummary {
  articles: ArticleSummary[]
}

export interface ArticleListParams {
  difficulty?: ArticleSummary['difficulty'] | ''
  article_type?: ArticleSummary['article_type'] | ''
  model_tag?: string
  sort?: 'latest' | 'hot' | 'featured'
  q?: string
  page?: number
  page_size?: number
}

export interface ArticlePayload {
  title: string
  content: string
  difficulty: ArticleSummary['difficulty']
  article_type: ArticleSummary['article_type']
  model_tags: string[]
  custom_tags: string[]
  related_skill_id?: number | null
  series_id?: number | null
  series_order?: number | null
}

export async function listArticles(params: ArticleListParams = {}) {
  const response = await api.get<ArticleSummary[]>('/workshop', { params })
  return response.data
}

export async function listFeaturedArticles(limit = 6) {
  const response = await api.get<ArticleSummary[]>('/workshop/featured', { params: { limit } })
  return response.data
}

export async function listRecommendedArticles(limit = 8) {
  const response = await api.get<RecommendedArticle[]>('/workshop/recommended', { params: { limit } })
  return response.data
}

export async function searchArticles(
  params: Pick<ArticleListParams, 'q' | 'difficulty' | 'article_type' | 'model_tag'> & { limit?: number },
) {
  const response = await api.get<ArticleSearchResult>('/search/articles', { params })
  return response.data
}

export async function listMyArticles(status?: ArticleSummary['status']) {
  const response = await api.get<ArticleSummary[]>('/workshop/mine', {
    params: status ? { status } : undefined,
  })
  return response.data
}

export async function getArticle(articleId: number) {
  const response = await api.get<ArticleDetail>(`/workshop/${articleId}`)
  return response.data
}

export async function listRelatedArticles(articleId: number, limit = 4) {
  const response = await api.get<RecommendedArticle[]>(`/workshop/${articleId}/related`, { params: { limit } })
  return response.data
}

export async function createArticle(payload: ArticlePayload) {
  const response = await api.post<ArticleDetail>('/workshop', payload)
  return response.data
}

export async function updateArticle(articleId: number, payload: Partial<ArticlePayload>) {
  const response = await api.patch<ArticleDetail>(`/workshop/${articleId}`, payload)
  return response.data
}

export async function publishArticle(articleId: number) {
  const response = await api.post<ArticleDetail>(`/workshop/${articleId}/publish`)
  return response.data
}

export async function archiveArticle(articleId: number) {
  const response = await api.delete<{ message: string }>(`/workshop/${articleId}`)
  return response.data
}

export async function listArticleComments(articleId: number) {
  const response = await api.get<ArticleComment[]>(`/workshop/${articleId}/comments`)
  return response.data
}

export async function voteArticle(articleId: number, value: 'UP' | 'DOWN') {
  const response = await api.post<{ net_votes: number; my_vote: 'UP' | 'DOWN' | null }>(
    `/workshop/${articleId}/vote`,
    { value },
  )
  return response.data
}

export async function removeArticleVote(articleId: number) {
  const response = await api.delete<{ net_votes: number; my_vote: null }>(`/workshop/${articleId}/vote`)
  return response.data
}

export async function addArticleComment(articleId: number, content: string, parentId?: number) {
  const response = await api.post(`/workshop/${articleId}/comments`, {
    content,
    parent_id: parentId,
  })
  return response.data
}

export async function pinArticleComment(articleId: number, commentId: number) {
  const response = await api.post<ArticleComment>(`/workshop/${articleId}/pin-comment`, {
    comment_id: commentId,
  })
  return response.data
}

export async function voteArticleComment(commentId: number, value: 'UP' | 'DOWN') {
  const response = await api.post<{ net_votes: number; my_vote: 'UP' | 'DOWN' | null; is_collapsed: boolean }>(
    `/workshop/comments/${commentId}/vote`,
    { value },
  )
  return response.data
}

export async function removeArticleCommentVote(commentId: number) {
  const response = await api.delete<{ net_votes: number; my_vote: null; is_collapsed: boolean }>(
    `/workshop/comments/${commentId}/vote`,
  )
  return response.data
}

export async function listSeries(limit = 12) {
  const response = await api.get<SeriesSummary[]>('/workshop/series', { params: { limit } })
  return response.data
}

export async function getSeries(seriesId: number) {
  const response = await api.get<SeriesDetail>(`/workshop/series/${seriesId}`)
  return response.data
}

export async function createSeries(payload: { title: string; description?: string; cover_url?: string }) {
  const response = await api.post<SeriesDetail>('/workshop/series', payload)
  return response.data
}

export async function updateSeries(
  seriesId: number,
  payload: { title?: string; description?: string; cover_url?: string },
) {
  const response = await api.patch<SeriesDetail>(`/workshop/series/${seriesId}`, payload)
  return response.data
}

export async function reorderSeriesArticles(seriesId: number, articleIds: number[]) {
  const response = await api.post<SeriesDetail>(`/workshop/series/${seriesId}/reorder`, {
    article_ids: articleIds,
  })
  return response.data
}
