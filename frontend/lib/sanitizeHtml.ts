import DOMPurify from "dompurify";

const HOMEWORK_ALLOWED_TAGS = [
  "div",
  "p",
  "span",
  "h1",
  "h2",
  "h3",
  "h4",
  "h5",
  "h6",
  "ul",
  "ol",
  "li",
  "table",
  "thead",
  "tbody",
  "tfoot",
  "tr",
  "td",
  "th",
  "img",
  "sup",
  "sub",
  "strong",
  "em",
  "b",
  "i",
  "u",
  "br",
  "hr",
  "pre",
  "code",
  "blockquote",
  "a",
  "section",
  "article",
];

const HOMEWORK_ALLOWED_ATTR = [
  "class",
  "src",
  "alt",
  "width",
  "height",
  "colspan",
  "rowspan",
  "href",
  "title",
  "rel",
  "target",
];

/** Defense-in-depth: sanitize HTML before dangerouslySetInnerHTML. */
export function sanitizeHomeworkHtml(html: string): string {
  if (!html) return "";
  return DOMPurify.sanitize(html, {
    ALLOWED_TAGS: HOMEWORK_ALLOWED_TAGS,
    ALLOWED_ATTR: HOMEWORK_ALLOWED_ATTR,
    ALLOW_DATA_ATTR: false,
  });
}
