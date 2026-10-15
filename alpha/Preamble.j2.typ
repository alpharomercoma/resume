// Alpha's resume theme. A single-column, ATS-friendly layout whose metrics were
// measured from the original FlowCV resume (A4, Roboto, 9pt body).
// RenderCV fills the templates in this folder; the layout lives here.

#let ink = rgb("#000000") // body text
#let muted = rgb("#333333") // name, headline, section titles, rules, dates, icons
#let margin-x = 28.35pt // 1cm
#let entry-gap = 5.25pt // between entries in a section
#let row-gap = 4.5pt // between one-line rows (skills, certifications)
#let section-gap = 7.35pt // above every section title

#set document(
  title: "{{ cv._plain_name|replace("\\", "\\\\")|replace("\"", "\\\"") }} – Resume",
  author: "{{ cv._plain_name|replace("\\", "\\\\")|replace("\"", "\\\"") }}",
  keywords: ("{{ cv.headline|replace("\\", "\\\\")|replace("\"", "\\\"") }}", "resume", "CV"),
)
#set page(
  paper: "{{ design.page.size }}",
  margin: (left: margin-x, right: margin-x, top: 26pt, bottom: margin-x),
)
// Line boxes use Roboto's hhea ascender/descender (1900/2048, 500/2048), the
// metrics a browser uses for "line-height: normal" (trimmed to FlowCV's 10.5pt
// pitch at 9pt), so lines land where the FlowCV original put them.
#set text(
  font: "Roboto",
  size: 9pt,
  fill: ink,
  lang: "en",
  hyphenate: false,
  ligatures: false,
  overhang: false, // a trailing period must not shift centered lines
  top-edge: 0.9277em,
  bottom-edge: -0.2390em,
)
#set par(justify: false, leading: 0pt, spacing: 0pt)
#set block(spacing: 0pt)
#set smartquote(enabled: false) // keep straight apostrophes, as typed
// A real U+2022 set inline, so the text layer reads "• Built ...". Lato's
// bullet is a 0.371em disc: at 8.1pt it matches FlowCV's 3pt disc while staying
// close enough to the 9pt body that text extractors keep it on the same line.
#let bullet-at(raise) = text(font: "Lato", size: 8.1pt, baseline: -raise, "•")
#let bullet = bullet-at(0.65pt)
#set list(marker: bullet, indent: 7.55pt, body-indent: 3.05pt, spacing: 0pt, tight: true)

// External-link mark after linked titles. A vector image tagged as a PDF
// artifact, so it never leaks an icon glyph into the text layer that ATS
// parsers and screen readers read.
#let link-icon = pdf.artifact(box(
  baseline: 0.1pt,
  image(
    bytes(
      "<svg xmlns='http://www.w3.org/2000/svg' viewBox='0 0 4.9 4.9' fill='none' stroke='#333333' stroke-width='0.38' stroke-linecap='square' stroke-linejoin='miter'><path d='M2.3 0.79H0.19V4.71H4.01V2.6'/><path d='M2.2 2.7L4.6 0.3'/><path d='M2.95 0.19H4.71V1.95'/></svg>",
    ),
    format: "svg",
    height: 4.9pt,
  ),
))
#let linked(it) = [#it#h(3pt)#link-icon#h(0.7pt)]

// The name line and section titles are real headings (H1 and H2 in the tagged
// PDF), styled here, so parsers and screen readers see the document outline.
#show heading: set text(weight: "regular")
#show heading: set block(above: 0pt, below: 0pt)
#show heading.where(level: 1): it => align(center, it.body)
#show heading.where(level: 2): it => {
  v(section-gap)
  block(breakable: false, {
    text(size: 10pt, weight: "bold", fill: muted, upper(it.body))
    v(0.6pt)
    block(width: 100%, height: 1.5pt, fill: muted)
    v(4.4pt)
  })
}

#let header(name, headline, contacts) = {
  set text(fill: muted)
  heading(level: 1, {
    text(size: 14pt, weight: "bold", name)
    text(size: 14pt, " ")
    h(3.4pt)
    text(size: 11pt, style: "italic", headline)
  })
  v(6.3pt)
  set text(fill: ink)
  align(center, contacts.join([ #h(4pt)|#h(4pt) ]))
}

#let intro(body) = {
  v(12.75pt)
  align(center, body)
}

// RenderCV wraps each entry's SUMMARY in #summary[...]; render it as is.
#let summary(body) = body

// One entry: a bold title line with the date flush right, then full-width
// lines (bullets or a note) underneath, so nothing wraps beside the date.
#let entry(title, date, body) = block(breakable: false, {
  // Title and date share one line of text, so extractors read them together.
  block[#title#h(1fr)#text(fill: muted, date)]
  body
})

// Indented plain line under an entry title (e.g. education honors).
#let entry-note(body) = pad(left: 7.2pt, body)

// Bulleted items in two columns, filled top-to-bottom so text extraction
// still reads them in source order.
#let bullet-columns(items) = {
  let per-column = calc.ceil(items.len() / 2)
  let column(cells) = {
    set list(indent: 0.8pt, body-indent: 2.6pt)
    for (i, cell) in cells.enumerate() {
      if i > 0 { v(row-gap) }
      list(cell)
    }
  }
  v(0.7pt)
  grid(
    columns: (1fr, 1fr),
    column-gutter: 17.9pt,
    column(items.slice(0, per-column)), column(items.slice(per-column)),
  )
}

// Every YAML section arrives here as (title, snake_case key, entry type, entries).
#let section(title, key, kind, items) = {
  if key == "summary" {
    intro(items.join())
    return
  }
  heading(level: 2, title)
  if kind == "BulletEntry" {
    bullet-columns(items)
  } else {
    let gap = if kind == "OneLineEntry" { row-gap } else { entry-gap }
    for (i, item) in items.enumerate() {
      if i > 0 { v(gap) }
      block(item)
    }
  }
}
