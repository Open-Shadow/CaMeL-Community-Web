export interface User {
  id: number
  username: string
  email: string
  credit_score: number
  avatar_url: string
  display_name: string
  level: string
  role: string
  created_at: string
}

export interface Skill {
  id: number
  name: string
  slug: string
  description: string
  category: string
  price: number | null
  pricing_model: string
  creator_id: number
  creator_name: string
  total_calls: number
  avg_rating: number
  created_at: string
}

export interface Bounty {
  id: number
  title: string
  description: string
  reward: number
  status: string
  creator: User
  created_at: string
  deadline: string
}

export interface Article {
  id: number
  title: string
  content: string
  author: User
  net_votes: number
  created_at: string
}

export type CreditTier = {
  name: string
  icon: string
  min: number
  max: number
  discount: number
}
