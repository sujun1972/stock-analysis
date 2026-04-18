'use client'

import dynamic from 'next/dynamic'
import { Loader } from 'lucide-react'
import type { NewStrategyFormData } from '../hooks/useNewStrategyForm'

// 动态导入 Monaco Editor (客户端组件)
const Editor = dynamic(() => import('@monaco-editor/react'), {
  ssr: false,
  loading: () => (
    <div className="flex h-[400px] items-center justify-center rounded-lg border bg-gray-50">
      <Loader className="h-8 w-8 animate-spin text-blue-600" />
    </div>
  ),
})

interface CodeEditorSectionProps {
  formData: NewStrategyFormData
  updateField: <K extends keyof NewStrategyFormData>(field: K, value: NewStrategyFormData[K]) => void
  isMobile: boolean
  validating: boolean
  onValidate: () => void
}

export function CodeEditorSection({
  formData,
  updateField,
  isMobile,
  validating,
  onValidate,
}: CodeEditorSectionProps) {
  return (
    <div className="rounded-lg border border-gray-200 bg-white p-4 sm:p-6">
      <h3 className="mb-4 text-lg font-semibold">
        策略代码 <span className="text-red-500">*</span>
      </h3>
      <div className="overflow-hidden rounded-lg border border-gray-300">
        {isMobile ? (
          <textarea
            value={formData.code}
            onChange={(e) => updateField('code', e.target.value)}
            className="w-full h-[400px] bg-gray-900 text-green-400 font-mono text-sm p-4 focus:outline-none focus:ring-2 focus:ring-blue-500"
            placeholder="# 示例:选股策略&#10;class MyStockSelectionStrategy:&#10;    &quot;&quot;&quot;&#10;    自定义选股策略&#10;    &quot;&quot;&quot;&#10;    def select_stocks(self, universe, features, date):&#10;        &quot;&quot;&quot;选择股票&quot;&quot;&quot;&#10;        # TODO: 实现你的选股逻辑&#10;        pass"
          />
        ) : (
          <Editor
            height="400px"
            defaultLanguage="python"
            value={formData.code}
            onChange={(value) => updateField('code', value || '')}
            theme="vs-dark"
            loading={<div className="flex h-[400px] items-center justify-center"><Loader className="h-8 w-8 animate-spin text-blue-600" /></div>}
            options={{
              minimap: { enabled: false },
              fontSize: 13,
              lineNumbers: 'on',
              scrollBeyondLastLine: false,
              automaticLayout: true,
              tabSize: 4,
              wordWrap: 'on',
              formatOnPaste: false,
              formatOnType: false,
              quickSuggestions: false,
              suggestOnTriggerCharacters: false,
              acceptSuggestionOnCommitCharacter: false,
              acceptSuggestionOnEnter: 'off',
              snippetSuggestions: 'none',
            }}
            defaultValue={`# 示例:选股策略
class MyStockSelectionStrategy:
    """
    自定义选股策略
    """
    def select_stocks(self, universe, features, date):
        """
        选择股票

        Args:
            universe: 股票池列表
            features: 特征数据
            date: 当前日期

        Returns:
            list: 选中的股票代码列表
        """
        # TODO: 实现你的选股逻辑
        pass
`}
          />
        )}
      </div>
      <div className="mt-4 flex gap-2">
        <button
          type="button"
          onClick={onValidate}
          disabled={validating || !formData.code}
          className="flex items-center justify-center gap-2 rounded-lg border border-blue-600 px-4 py-2 text-sm sm:text-base text-blue-600 hover:bg-blue-50 disabled:cursor-not-allowed disabled:opacity-50 w-full sm:w-auto"
        >
          {validating && <Loader className="h-4 w-4 animate-spin" />}
          验证代码
        </button>
      </div>
    </div>
  )
}
