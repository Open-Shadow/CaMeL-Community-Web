import { Progress } from '@/components/ui/progress';
import { CreditBadge, getNextLevelInfo, LEVEL_PRIVILEGES, LEVEL_CONFIG } from './credit-badge';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Check } from 'lucide-react';

interface CreditProgressProps {
  score: number;
  className?: string;
}

export function CreditProgress({ score, className }: CreditProgressProps) {
  const { currentLevel, nextLevel, progress, pointsNeeded } = getNextLevelInfo(score);
  const nextConfig = nextLevel ? LEVEL_CONFIG[nextLevel] : null;

  return (
    <Card className={className}>
      <CardHeader>
        <CardTitle className="flex items-center gap-2">
          <span>信用等级</span>
          <CreditBadge level={currentLevel} score={score} />
        </CardTitle>
      </CardHeader>
      <CardContent className="space-y-4">
        {/* 进度条 */}
        <div className="space-y-2">
          <div className="flex justify-between text-sm">
            <span className="text-muted-foreground">当前: {score} 分</span>
            {nextConfig ? (
              <span className="text-muted-foreground">
                距离 {nextConfig.icon} {nextConfig.name} 还需 {pointsNeeded} 分
              </span>
            ) : (
              <span className="text-amber-600 font-medium">已达到最高等级！</span>
            )}
          </div>
          <Progress value={progress} className="h-2" />
        </div>

        {/* 特权列表 */}
        <div className="space-y-3 pt-2">
          <h4 className="text-sm font-medium">当前特权</h4>
          <ul className="space-y-2">
            {Object.entries(LEVEL_PRIVILEGES).map(([level, privileges]) => {
              const config = LEVEL_CONFIG[level];
              const isUnlocked = LEVEL_PRIVILEGES[currentLevel] &&
                Object.keys(LEVEL_PRIVILEGES).indexOf(level) <=
                Object.keys(LEVEL_PRIVILEGES).indexOf(currentLevel);

              return (
                <li
                  key={level}
                  className={`flex items-start gap-2 text-sm ${
                    isUnlocked ? '' : 'opacity-50'
                  }`}
                >
                  <Check
                    className={`h-4 w-4 mt-0.5 shrink-0 ${
                      isUnlocked ? 'text-green-500' : 'text-gray-300'
                    }`}
                  />
                  <div>
                    <span className="font-medium">
                      {config.icon} {config.name}
                    </span>
                    <span className="text-muted-foreground">
                      {' '}: {privileges.join('、')}
                    </span>
                  </div>
                </li>
              );
            })}
          </ul>
        </div>
      </CardContent>
    </Card>
  );
}
