import ReactMarkdown from 'react-markdown';
import remarkGfm from 'remark-gfm';

const components = {
  a: ({ href, children, title }) => <a href={href} title={title} target="_blank" rel="noopener noreferrer">{children}</a>,
  table: ({ children }) => <div className="markdown-table-scroll"><table>{children}</table></div>,
};

export default function MarkdownContent({ children }) {
  return (
    <div className="markdown-content">
      <ReactMarkdown remarkPlugins={[remarkGfm]} skipHtml disallowedElements={['img']} components={components}>
        {typeof children === 'string' ? children : ''}
      </ReactMarkdown>
    </div>
  );
}
