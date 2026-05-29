/**
 * Minimal Markdown editor with live preview.
 *
 * Deliberately no third-party MD library — we already pay for shiki via
 * CopilotKit; pulling another markdown parser into the non-chat bundle
 * isn't worth it. This renderer covers the basics: headings, bold/italic,
 * inline code, fenced code, lists, links, paragraphs. Everything else
 * falls through to escaped plain text.
 */
import { useMemo, useState } from "react";
import { Eye, EyeOff, Bold, Italic, List, Code, Link as LinkIcon } from "lucide-react";
import { cn } from "./cn";

export interface MarkdownEditorProps {
  value: string;
  onChange: (v: string) => void;
  placeholder?: string;
  rows?: number;
  id?: string;
  "aria-invalid"?: boolean;
  "aria-describedby"?: string;
}

export function MarkdownEditor({
  value,
  onChange,
  placeholder,
  rows = 12,
  ...rest
}: MarkdownEditorProps) {
  const [showPreview, setShowPreview] = useState(true);

  const wrapSelection = (before: string, after: string = before) => {
    const ta = document.getElementById(rest.id ?? "") as HTMLTextAreaElement | null;
    if (!ta) {
      onChange(value + before + after);
      return;
    }
    const start = ta.selectionStart;
    const end = ta.selectionEnd;
    const selected = value.slice(start, end);
    const next = value.slice(0, start) + before + selected + after + value.slice(end);
    onChange(next);
    requestAnimationFrame(() => {
      ta.focus();
      ta.selectionStart = start + before.length;
      ta.selectionEnd = end + before.length;
    });
  };

  const insertLineStart = (prefix: string) => {
    const ta = document.getElementById(rest.id ?? "") as HTMLTextAreaElement | null;
    if (!ta) {
      onChange(prefix + value);
      return;
    }
    const start = ta.selectionStart;
    const lineStart = value.lastIndexOf("\n", start - 1) + 1;
    const next = value.slice(0, lineStart) + prefix + value.slice(lineStart);
    onChange(next);
    requestAnimationFrame(() => {
      ta.focus();
      ta.selectionStart = start + prefix.length;
      ta.selectionEnd = start + prefix.length;
    });
  };

  return (
    <div className="rounded-input bg-field border border-transparent focus-within:border-ink transition-colors duration-180 ease-pirsch overflow-hidden">
      <div className="flex items-center justify-between gap-1 px-2 py-1.5 border-b border-ink/5">
        <div className="flex items-center gap-0.5">
          <ToolbarButton onClick={() => wrapSelection("**")} label="Negrita">
            <Bold size={12} />
          </ToolbarButton>
          <ToolbarButton onClick={() => wrapSelection("_")} label="Cursiva">
            <Italic size={12} />
          </ToolbarButton>
          <ToolbarButton onClick={() => wrapSelection("`")} label="Código en línea">
            <Code size={12} />
          </ToolbarButton>
          <ToolbarButton onClick={() => insertLineStart("- ")} label="Lista">
            <List size={12} />
          </ToolbarButton>
          <ToolbarButton onClick={() => wrapSelection("[", "](url)")} label="Enlace">
            <LinkIcon size={12} />
          </ToolbarButton>
        </div>
        <button
          type="button"
          onClick={() => setShowPreview((v) => !v)}
          aria-pressed={showPreview}
          className="inline-flex items-center gap-1 text-[11px] text-stone hover:text-ink transition-colors px-2 py-1 rounded-btn hover:bg-field"
        >
          {showPreview ? <EyeOff size={11} /> : <Eye size={11} />}
          {showPreview ? "Ocultar preview" : "Ver preview"}
        </button>
      </div>
      <div className={cn("grid", showPreview && "md:grid-cols-2")}>
        <textarea
          {...rest}
          rows={rows}
          value={value}
          onChange={(e) => onChange(e.target.value)}
          placeholder={placeholder}
          className="block w-full p-4 text-[13px] font-mono leading-relaxed text-ink bg-transparent outline-none placeholder:text-stone resize-y min-h-[200px]"
        />
        {showPreview && (
          <div
            className="hidden md:block border-l border-ink/5 p-4 text-sm leading-relaxed overflow-auto max-h-[60vh] prose-tight"
            aria-label="Vista previa"
          >
            <MarkdownPreview source={value} />
          </div>
        )}
      </div>
    </div>
  );
}

function ToolbarButton({
  onClick,
  label,
  children,
}: {
  onClick: () => void;
  label: string;
  children: React.ReactNode;
}) {
  return (
    <button
      type="button"
      onClick={onClick}
      aria-label={label}
      title={label}
      className="inline-flex items-center justify-center w-7 h-7 rounded-btn text-stone hover:text-ink hover:bg-black/[0.06] transition-colors duration-180"
    >
      {children}
    </button>
  );
}

/**
 * Tiny markdown → HTML renderer. Not a full implementation — only what's
 * common in user notes. Falls back to escaped text for anything unknown.
 */
function MarkdownPreview({ source }: { source: string }) {
  const html = useMemo(() => renderMarkdown(source), [source]);
  if (!source.trim()) {
    return <p className="text-stone italic">La vista previa aparece aquí.</p>;
  }
  return <div dangerouslySetInnerHTML={{ __html: html }} />;
}

function escapeHtml(s: string): string {
  return s
    .replace(/&/g, "&amp;")
    .replace(/</g, "&lt;")
    .replace(/>/g, "&gt;")
    .replace(/"/g, "&quot;");
}

function renderInline(s: string): string {
  let out = escapeHtml(s);
  // inline code
  out = out.replace(/`([^`\n]+)`/g, '<code class="bg-canvas px-1.5 py-0.5 rounded text-[12px]">$1</code>');
  // bold
  out = out.replace(/\*\*([^*\n]+)\*\*/g, "<strong>$1</strong>");
  // italic (underscore avoids clashing with bold)
  out = out.replace(/(^|[\s(])_([^_\n]+)_(?=[\s).,;:!?]|$)/g, "$1<em>$2</em>");
  // links
  out = out.replace(
    /\[([^\]]+)\]\(([^\s)]+)\)/g,
    '<a href="$2" class="text-ink underline-offset-2 hover:underline" target="_blank" rel="noreferrer">$1</a>',
  );
  return out;
}

function renderMarkdown(src: string): string {
  const lines = src.split("\n");
  const out: string[] = [];
  let i = 0;
  while (i < lines.length) {
    const line = lines[i];

    // Fenced code
    if (line.startsWith("```")) {
      const block: string[] = [];
      i++;
      while (i < lines.length && !lines[i].startsWith("```")) {
        block.push(lines[i]);
        i++;
      }
      i++;
      out.push(
        `<pre class="bg-canvas border border-ink/8 rounded-card p-3 my-2 text-[12px] font-mono overflow-x-auto">${escapeHtml(
          block.join("\n"),
        )}</pre>`,
      );
      continue;
    }

    // Headings
    const hMatch = /^(#{1,6})\s+(.*)$/.exec(line);
    if (hMatch) {
      const level = hMatch[1].length;
      const size = ["text-2xl", "text-xl", "text-lg", "text-base", "text-sm", "text-sm"][level - 1];
      out.push(
        `<h${level} class="${size} font-medium tracking-tight text-ink mt-3 mb-1.5">${renderInline(hMatch[2])}</h${level}>`,
      );
      i++;
      continue;
    }

    // Lists (consume contiguous items)
    if (/^(\s*[-*]\s+)/.test(line)) {
      const items: string[] = [];
      while (i < lines.length && /^(\s*[-*]\s+)/.test(lines[i])) {
        items.push(lines[i].replace(/^(\s*[-*]\s+)/, ""));
        i++;
      }
      out.push(
        `<ul class="list-disc pl-5 my-2 space-y-1">${items
          .map((it) => `<li>${renderInline(it)}</li>`)
          .join("")}</ul>`,
      );
      continue;
    }

    // Blank line
    if (!line.trim()) {
      i++;
      continue;
    }

    // Paragraph (consume contiguous non-blank lines)
    const para: string[] = [line];
    i++;
    while (i < lines.length && lines[i].trim() && !/^(#{1,6}\s|[-*]\s|```)/.test(lines[i])) {
      para.push(lines[i]);
      i++;
    }
    out.push(`<p class="my-2">${renderInline(para.join("\n"))}</p>`);
  }
  return out.join("\n");
}
