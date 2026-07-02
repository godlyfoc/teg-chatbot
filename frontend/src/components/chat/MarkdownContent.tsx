import { Children, isValidElement, memo, useMemo } from "react";
import ReactMarkdown from "react-markdown";
import remarkGfm from "remark-gfm";
import remarkBreaks from "remark-breaks";
import rehypeHighlight from "rehype-highlight";
import type { Components } from "react-markdown";
import "highlight.js/styles/github.css";

interface Props {
  content: string;
}

function getLinkText(children: React.ReactNode): string {
  return Children.toArray(children)
    .map((child) => {
      if (typeof child === "string" || typeof child === "number") return String(child);
      if (isValidElement<{ children?: React.ReactNode }>(child)) {
        return getLinkText(child.props.children);
      }
      return "";
    })
    .join("")
    .trim();
}

function isCitationLink(href: string | undefined, children: React.ReactNode): boolean {
  if (!href?.startsWith("http")) return false;
  return /^\d{1,2}$/.test(getLinkText(children));
}

const markdownComponents: Components = {
  a: ({ href, children, ...props }) => {
    if (isCitationLink(href, children)) {
      return (
        <a
          href={href}
          className="markdown__citation"
          target="_blank"
          rel="noopener noreferrer"
          title={`Source ${getLinkText(children)}`}
          {...props}
        >
          {children}
        </a>
      );
    }
    return (
      <a href={href} target="_blank" rel="noopener noreferrer" {...props}>
        {children}
      </a>
    );
  },
  table: ({ children }) => (
    <div className="markdown__table-wrap">
      <table>{children}</table>
    </div>
  ),
  pre: ({ children }) => <pre className="markdown__pre">{children}</pre>,
  code: ({ className, children, ...props }) => {
    const isBlock = className?.includes("language-");
    if (isBlock) {
      return (
        <code className={className} {...props}>
          {children}
        </code>
      );
    }
    return (
      <code className="markdown__inline-code" {...props}>
        {children}
      </code>
    );
  },
};

function MarkdownContent({ content }: Props) {
  const plugins = useMemo(
    () => ({
      remark: [remarkGfm, remarkBreaks],
      rehype: [rehypeHighlight],
    }),
    [],
  );

  if (!content) return null;

  return (
    <div className="markdown">
      <ReactMarkdown
        remarkPlugins={plugins.remark}
        rehypePlugins={plugins.rehype}
        components={markdownComponents}
      >
        {content}
      </ReactMarkdown>
    </div>
  );
}

export default memo(MarkdownContent);
