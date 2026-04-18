'use client'

import { AlertCircle, Loader, Save } from 'lucide-react'
import { PageHeader } from '@/components/common/PageHeader'
import { useIsMobile, useNewStrategyForm, useNewStrategyActions } from './hooks'
import {
  ValidationResult,
  BasicInfoSection,
  MetaInfoSection,
  CodeEditorSection,
} from './components'

export default function NewStrategyPage() {
  const isMobile = useIsMobile()
  const { formData, updateField } = useNewStrategyForm()
  const {
    loading,
    validating,
    validationResult,
    error,
    handleValidate,
    handleSubmit,
    handleCancel,
  } = useNewStrategyActions(formData)

  return (
    <div className="p-4 sm:p-6">
      {/* 页面头部 */}
      <PageHeader
        title="创建新策略"
        description="填写策略信息并验证代码"
      />

      {/* 错误提示 */}
      {error && (
        <div className="mb-6 rounded-lg border border-red-200 bg-red-50 p-4">
          <div className="flex items-center gap-2">
            <AlertCircle className="h-5 w-5 text-red-600" />
            <p className="text-red-800">{error}</p>
          </div>
        </div>
      )}

      {/* 验证结果 */}
      {validationResult && (
        <ValidationResult validationResult={validationResult} />
      )}

      {/* 表单 */}
      <form onSubmit={handleSubmit} className="space-y-6">
        <div className="grid gap-6 grid-cols-1 lg:grid-cols-2">
          {/* 基本信息 */}
          <BasicInfoSection formData={formData} updateField={updateField} />

          {/* 元信息 */}
          <MetaInfoSection formData={formData} updateField={updateField} />
        </div>

        {/* 策略代码 */}
        <CodeEditorSection
          formData={formData}
          updateField={updateField}
          isMobile={isMobile}
          validating={validating}
          onValidate={handleValidate}
        />

        {/* 提交按钮 */}
        <div className="flex flex-row gap-2 sm:gap-3">
          <button
            type="submit"
            disabled={loading}
            className="flex flex-1 sm:flex-initial items-center justify-center gap-2 rounded-lg bg-blue-600 px-4 sm:px-6 py-2.5 text-sm sm:text-base text-white hover:bg-blue-700 disabled:cursor-not-allowed disabled:opacity-50"
          >
            {loading ? (
              <Loader className="h-4 w-4 animate-spin" />
            ) : (
              <Save className="h-4 w-4" />
            )}
            创建策略
          </button>
          <button
            type="button"
            onClick={handleCancel}
            className="flex-1 sm:flex-initial rounded-lg border border-gray-300 px-4 sm:px-6 py-2.5 text-sm sm:text-base text-gray-700 hover:bg-gray-50"
          >
            取消
          </button>
        </div>
      </form>
    </div>
  )
}
