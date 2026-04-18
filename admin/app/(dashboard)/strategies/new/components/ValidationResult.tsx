'use client'

import { AlertCircle, CheckCircle } from 'lucide-react'

interface ValidationResultProps {
  validationResult: any
}

export function ValidationResult({ validationResult }: ValidationResultProps) {
  return (
    <div
      className={`mb-6 rounded-lg border p-4 ${
        validationResult.is_valid
          ? 'border-green-200 bg-green-50'
          : 'border-red-200 bg-red-50'
      }`}
    >
      <div className="flex items-center gap-2">
        {validationResult.is_valid ? (
          <>
            <CheckCircle className="h-5 w-5 text-green-600" />
            <p className="text-green-800">代码验证通过</p>
          </>
        ) : (
          <>
            <AlertCircle className="h-5 w-5 text-red-600" />
            <p className="text-red-800">代码验证失败</p>
          </>
        )}
      </div>
      {validationResult.errors && validationResult.errors.length > 0 && (
        <div className="mt-2">
          <div className="text-sm font-semibold text-red-800">错误:</div>
          <ul className="ml-4 list-disc text-sm text-red-700">
            {validationResult.errors.map((err: string, i: number) => (
              <li key={i}>{err}</li>
            ))}
          </ul>
        </div>
      )}
      {validationResult.warnings && validationResult.warnings.length > 0 && (
        <div className="mt-2">
          <div className="text-sm font-semibold text-yellow-800">警告:</div>
          <ul className="ml-4 list-disc text-sm text-yellow-700">
            {validationResult.warnings.map((warn: string, i: number) => (
              <li key={i}>{warn}</li>
            ))}
          </ul>
        </div>
      )}
      <div className="mt-2 text-sm">
        <span className="font-semibold">风险等级:</span>{' '}
        <span
          className={`ml-2 rounded-full px-2 py-1 text-xs font-semibold ${
            validationResult.risk_level === 'safe'
              ? 'bg-green-100 text-green-800'
              : validationResult.risk_level === 'low'
              ? 'bg-blue-100 text-blue-800'
              : validationResult.risk_level === 'medium'
              ? 'bg-yellow-100 text-yellow-800'
              : 'bg-red-100 text-red-800'
          }`}
        >
          {validationResult.risk_level}
        </span>
      </div>
    </div>
  )
}
