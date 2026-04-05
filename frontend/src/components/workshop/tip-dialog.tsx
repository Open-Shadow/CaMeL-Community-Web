import { useState } from 'react'
import { Dialog, DialogContent, DialogHeader, DialogTitle } from '@/components/ui/dialog'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import axios from 'axios'

const PRESET_AMOUNTS = [1, 5, 10, 20]

interface TipDialogProps {
  articleId: number
  articleTitle: string
  open: boolean
  onClose: () => void
  onSuccess?: (amount: number) => void
}

export function TipDialog({ articleId, articleTitle, open, onClose, onSuccess }: TipDialogProps) {
  const [amount, setAmount] = useState('')
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState('')

  const handleTip = async () => {
    const val = parseFloat(amount)
    if (!val || val < 0.01) { setError('最低打赏 $0.01'); return }
    setLoading(true); setError('')
    try {
      await axios.post(`/api/workshop/articles/${articleId}/tip`, { amount: val })
      onSuccess?.(val)
      onClose()
    } catch (e: any) {
      setError(e.response?.data?.detail || '打赏失败')
    } finally {
      setLoading(false)
    }
  }

  return (
    <Dialog open={open} onOpenChange={onClose}>
      <DialogContent className="max-w-sm">
        <DialogHeader>
          <DialogTitle>打赏《{articleTitle}》</DialogTitle>
        </DialogHeader>
        <div className="space-y-4">
          <div className="flex gap-2">
            {PRESET_AMOUNTS.map(a => (
              <Button key={a} variant="outline" size="sm" onClick={() => setAmount(String(a))}>
                ${a}
              </Button>
            ))}
          </div>
          <Input
            type="number"
            min="0.01"
            step="0.01"
            placeholder="自定义金额"
            value={amount}
            onChange={e => setAmount(e.target.value)}
          />
          {error && <p className="text-sm text-destructive">{error}</p>}
          <Button className="w-full" onClick={handleTip} disabled={loading}>
            {loading ? '处理中...' : '确认打赏'}
          </Button>
        </div>
      </DialogContent>
    </Dialog>
  )
}
