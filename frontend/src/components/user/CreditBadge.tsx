import { CREDIT_TIERS } from '@/lib/constants'

interface CreditBadgeProps {
  score: number
}

export function CreditBadge({ score }: CreditBadgeProps) {
  const tier = CREDIT_TIERS.find((t) => score >= t.min && score <= t.max) || CREDIT_TIERS[0]
  return (
    <span className="inline-flex items-center gap-1">
      <span>{tier.icon}</span>
      <span>{tier.name}</span>
      <span>({score})</span>
    </span>
  )
}
