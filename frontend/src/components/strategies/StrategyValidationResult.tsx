/**
 * 策略验证结果展示组件
 * 显示策略代码或配置的验证结果（错误、警告）
 */

'use client'

import { memo } from 'react'
import { Alert, AlertDescription, AlertTitle } from '@/components/ui/alert'
import { CheckCircle, XCircle, AlertCircle } from 'lucide-react'

interface ValidationError {
  type: string
  message: string
}

interface StrategyValidationResultProps {
  isValid: boolean
  errors?: ValidationError[]
  warnings?: ValidationError[]
}

const StrategyValidationResult = memo(function StrategyValidationResult({
  isValid,
  errors = [],
  warnings = []
}: StrategyValidationResultProps) {
  if (isValid && errors.length === 0 && warnings.length === 0) {
    return (
      <Alert className="border-green-200 bg-green-50 dark:bg-green-900/20">
        <CheckCircle className="h-4 w-4 text-green-600" />
        <AlertTitle className="text-green-800 dark:text-green-200">验证通过</AlertTitle>
        <AlertDescription className="text-green-700 dark:text-green-300">
          策略验证成功，没有发现错误或警告
        </AlertDescription>
      </Alert>
    )
  }

  return (
    <div className="space-y-3">
      {/* 错误信息 */}
      {errors.length > 0 && (
        <Alert variant="destructive">
          <XCircle className="h-4 w-4" />
          <AlertTitle>验证失败 ({errors.length} 个错误)</AlertTitle>
          <AlertDescription>
            <ul className="list-disc list-inside space-y-1 mt-2">
              {errors.map((error, idx) => (
                <li key={idx} className="text-sm">
                  <span className="font-medium">[{error.type}]</span> {error.message}
                </li>
              ))}
            </ul>
          </AlertDescription>
        </Alert>
      )}

      {/* 警告信息 */}
      {warnings.length > 0 && (
        <Alert className="border-yellow-200 bg-yellow-50 dark:bg-yellow-900/20">
          <AlertCircle className="h-4 w-4 text-yellow-600" />
          <AlertTitle className="text-yellow-800 dark:text-yellow-200">
            验证警告 ({warnings.length} 个警告)
          </AlertTitle>
          <AlertDescription className="text-yellow-700 dark:text-yellow-300">
            <ul className="list-disc list-inside space-y-1 mt-2">
              {warnings.map((warning, idx) => (
                <li key={idx} className="text-sm">
                  <span className="font-medium">[{warning.type}]</span> {warning.message}
                </li>
              ))}
            </ul>
          </AlertDescription>
        </Alert>
      )}

      {/* 通过但有警告 */}
      {isValid && warnings.length > 0 && errors.length === 0 && (
        <Alert className="border-green-200 bg-green-50 dark:bg-green-900/20">
          <CheckCircle className="h-4 w-4 text-green-600" />
          <AlertTitle className="text-green-800 dark:text-green-200">
            验证通过 (但有 {warnings.length} 个警告)
          </AlertTitle>
          <AlertDescription className="text-green-700 dark:text-green-300">
            策略可以使用，但建议修复上述警告以获得更好的性能和稳定性
          </AlertDescription>
        </Alert>
      )}
    </div>
  )
})

StrategyValidationResult.displayName = 'StrategyValidationResult'

export default StrategyValidationResult
