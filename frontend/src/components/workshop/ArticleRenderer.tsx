interface ArticleRendererProps {
  content: string
}

export function ArticleRenderer({ content }: ArticleRendererProps) {
  return (
    <article
      className="space-y-4 text-[15px] leading-7 text-slate-800 [&_a]:text-sky-700 [&_a]:underline [&_blockquote]:border-l-4 [&_blockquote]:border-slate-300 [&_blockquote]:bg-muted [&_blockquote]:px-4 [&_blockquote]:py-3 [&_code]:rounded [&_code]:bg-slate-100 [&_code]:px-1.5 [&_code]:py-0.5 [&_h1]:mt-8 [&_h1]:text-3xl [&_h1]:font-bold [&_h2]:mt-8 [&_h2]:border-t [&_h2]:pt-6 [&_h2]:text-2xl [&_h2]:font-semibold [&_h3]:mt-6 [&_h3]:text-xl [&_h3]:font-semibold [&_img]:rounded-xl [&_img]:border [&_p]:my-4 [&_pre]:my-5 [&_pre]:overflow-x-auto [&_pre]:rounded-xl [&_pre]:bg-slate-950 [&_pre]:p-4 [&_pre]:text-sm [&_pre]:text-slate-100 [&_table]:my-6 [&_table]:w-full [&_table]:border-collapse [&_tbody_td]:border [&_tbody_td]:px-3 [&_tbody_td]:py-2 [&_thead_th]:border [&_thead_th]:bg-slate-100 [&_thead_th]:px-3 [&_thead_th]:py-2 [&_ul]:my-4 [&_ul]:list-disc [&_ul]:pl-6"
      dangerouslySetInnerHTML={{ __html: content }}
    />
  )
}
