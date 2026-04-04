export interface User {
  id: number
  username: string
  email: string
  creditScore: number
  avatarUrl?: string
  createdAt: string
}

export interface Skill {
  id: number
  name: string
  description: string
  price: number
  author: User
  rating: number
  callCount: number
  createdAt: string
}

export interface Bounty {
  id: number
  title: string
  description: string
  reward: number
  status: 'open' | 'in_progress' | 'completed' | 'cancelled'
  author: User
  createdAt: string
  deadline?: string
}

export interface Article {
  id: number
  title: string
  content: string
  author: User
  voteCount: number
  createdAt: string
}

export type CreditTier = {
  name: string
  icon: string
  min: number
  max: number
  discount: number
}
