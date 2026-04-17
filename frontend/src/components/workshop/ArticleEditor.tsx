import { useEffect } from 'react'
import { EditorContent, useEditor } from '@tiptap/react'
import StarterKit from '@tiptap/starter-kit'
import { Bold, Code2, Heading2, List, ListOrdered, Quote, RotateCcw } from 'lucide-react'

import { Button } from '@/components/ui/button'

interface ArticleEditorProps {
  value: string
  onChange: (value: string) => void
}

export const DEFAULT_ARTICLE_TEMPLATE = `
<h1>请用动词开头，写清楚解决了什么问题</h1>
<h2>问题（Problem）</h2>
<p>描述你遇到的具体场景、限制条件和触发原因。</p>
<h2>方案（Solution）</h2>
<p>说明你的思路、关键步骤、配置或代码片段。</p>
<pre><code class="language-bash"># 在这里补充关键命令或代码
</code></pre>
<h2>效果（Result）</h2>
<p>说明结果、收益和数据变化。</p>
<h2>注意事项（Caveats）</h2>
<p>记录边界条件、风险和不适用场景。</p>
<h2>关联 Skill</h2>
<p>如有可复用 Skill，可在下方表单中选择并关联。</p>
`.trim()

export function ArticleEditor({ value, onChange }: ArticleEditorProps) {
  const editor = useEditor({
    extensions: [StarterKit],
    content: value || DEFAULT_ARTICLE_TEMPLATE,
    immediatelyRender: false,
    onUpdate: ({ editor: activeEditor }) => {
      onChange(activeEditor.getHTML())
    },
    editorProps: {
      attributes: {
        class:
          'min-h-[420px] rounded-b-xl border-x border-b border-border bg-background px-5 py-4 focus:outline-none [&_h1]:mb-4 [&_h1]:text-3xl [&_h1]:font-bold [&_h2]:mb-3 [&_h2]:mt-8 [&_h2]:text-xl [&_h2]:font-semibold [&_p]:mb-4 [&_p]:leading-7 [&_pre]:mb-4 [&_pre]:overflow-x-auto [&_pre]:rounded-lg [&_pre]:bg-slate-950 [&_pre]:p-4 [&_pre]:text-sm [&_pre]:text-slate-100 [&_blockquote]:border-l-4 [&_blockquote]:border-slate-300 [&_blockquote]:pl-4 [&_ul]:mb-4 [&_ul]:list-disc [&_ul]:pl-6 [&_ol]:mb-4 [&_ol]:list-decimal [&_ol]:pl-6',
      },
    },
  })

  useEffect(() => {
    if (!editor) return
    if (value && value !== editor.getHTML()) {
      editor.commands.setContent(value, false)
    }
    if (!value && editor.getHTML() !== DEFAULT_ARTICLE_TEMPLATE) {
      editor.commands.setContent(DEFAULT_ARTICLE_TEMPLATE, false)
    }
  }, [editor, value])

  if (!editor) {
    return <div className="rounded-xl border p-4 text-sm text-muted-foreground">编辑器加载中...</div>
  }

  return (
    <div className="rounded-xl bg-muted/70">
      <div className="flex flex-wrap gap-2 rounded-t-xl border border-border bg-card p-3">
        <Button type="button" variant="outline" size="sm" onClick={() => editor.chain().focus().toggleBold().run()}>
          <Bold className="mr-1 h-4 w-4" />
          加粗
        </Button>
        <Button
          type="button"
          variant="outline"
          size="sm"
          onClick={() => editor.chain().focus().toggleHeading({ level: 2 }).run()}
        >
          <Heading2 className="mr-1 h-4 w-4" />
          小标题
        </Button>
        <Button type="button" variant="outline" size="sm" onClick={() => editor.chain().focus().toggleBulletList().run()}>
          <List className="mr-1 h-4 w-4" />
          列表
        </Button>
        <Button type="button" variant="outline" size="sm" onClick={() => editor.chain().focus().toggleOrderedList().run()}>
          <ListOrdered className="mr-1 h-4 w-4" />
          编号
        </Button>
        <Button type="button" variant="outline" size="sm" onClick={() => editor.chain().focus().toggleCodeBlock().run()}>
          <Code2 className="mr-1 h-4 w-4" />
          代码块
        </Button>
        <Button type="button" variant="outline" size="sm" onClick={() => editor.chain().focus().toggleBlockquote().run()}>
          <Quote className="mr-1 h-4 w-4" />
          引用
        </Button>
        <Button
          type="button"
          variant="ghost"
          size="sm"
          className="ml-auto"
          onClick={() => editor.commands.setContent(DEFAULT_ARTICLE_TEMPLATE)}
        >
          <RotateCcw className="mr-1 h-4 w-4" />
          重置模板
        </Button>
      </div>
      <EditorContent editor={editor} />
    </div>
  )
}
