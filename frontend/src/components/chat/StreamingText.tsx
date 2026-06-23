import ReactMarkdown from 'react-markdown';
import remarkGfm from 'remark-gfm';

interface Props {
  content: string;
}

export function StreamingText({ content }: Props) {
  return (
    <div className="flex justify-start msg-enter mb-4">
      <div className="max-w-[80%]">
        <div className="px-4 py-3 rounded-2xl bg-white border border-gray-100 shadow-sm rounded-bl-md streaming-cursor">
          <div className="markdown-body text-sm text-gray-800 prose-sm">
            <ReactMarkdown remarkPlugins={[remarkGfm]}>
              {content || ' '}
            </ReactMarkdown>
          </div>
        </div>
      </div>
    </div>
  );
}
