"use client"

import { Button } from "@/components/ui/button"
import { Dialog, DialogContent, DialogHeader, DialogTitle } from "@/components/ui/dialog"
import { FileTextIcon, RefreshCwIcon, CopyIcon } from "lucide-react"
import { toast } from "sonner"

interface PromptPreviewDialogProps {
  open: boolean
  onOpenChange: (open: boolean) => void
  promptText: string
  promptDate: string
  isLoading: boolean
}

export function PromptPreviewDialog({
  open,
  onOpenChange,
  promptText,
  promptDate,
  isLoading,
}: PromptPreviewDialogProps) {
  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent className="max-w-4xl max-h-[80vh] flex flex-col">
        <DialogHeader>
          <DialogTitle className="flex items-center gap-2">
            <FileTextIcon className="h-5 w-5" />
            打板专题 AI 分析提示词
            {promptDate && <span className="text-sm font-normal text-muted-foreground">（{promptDate}）</span>}
          </DialogTitle>
        </DialogHeader>
        <div className="flex-1 overflow-hidden flex flex-col gap-3 min-h-0">
          {isLoading ? (
            <div className="flex items-center justify-center py-12 text-muted-foreground">
              <RefreshCwIcon className="h-6 w-6 animate-spin mr-2" />
              正在从打板专题数据库生成提示词...
            </div>
          ) : (
            <>
              <div className="flex justify-end">
                <Button
                  variant="outline"
                  size="sm"
                  onClick={() => {
                    navigator.clipboard.writeText(promptText)
                    toast.success("提示词已复制到剪贴板")
                  }}
                >
                  <CopyIcon className="h-4 w-4 mr-1" />
                  复制全文
                </Button>
              </div>
              <div className="flex-1 overflow-auto rounded-md border bg-muted/40 min-h-0">
                <pre className="p-4 text-xs leading-relaxed whitespace-pre-wrap font-mono">
                  {promptText}
                </pre>
              </div>
            </>
          )}
        </div>
      </DialogContent>
    </Dialog>
  )
}
