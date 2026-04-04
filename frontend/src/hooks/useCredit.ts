import { CREDIT_TIERS } from '@/lib/constants'

export function useCredit(score: number) {
  const tier = CREDIT_TIERS.find((t) => score >= t.min && score <= t.max) || CREDIT_TIERS[0]
  return { tier, discount: tier.discount }
}
