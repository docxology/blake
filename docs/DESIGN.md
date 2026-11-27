# Blake dashboard component contract

## 1. Atmosphere and identity

An evidence workbench for researchers: the work, its source, and the scope of a
claim remain visible together. Preserve the existing Streamlit component system.
The release update adds evidence and search states without a framework migration.

## 2. Color

Use the active Streamlit theme bindings: `theme.backgroundColor`,
`theme.secondaryBackgroundColor`, `theme.textColor`, and `theme.primaryColor`.
Light and dark values come from the selected native theme; application components
must not introduce CSS color literals. Use explicit status text rather than color
alone. Native input validation and keyboard focus remain visible.

## 3. Typography

Use `theme.font` through native title, heading, body, caption, and metric roles.
Use native text/code elements for provider excerpts, identifiers and commands.
Provider text is plain text, never application HTML. No downloaded fonts.

## 4. Spacing and layout

The existing wide page, collapsible sidebar and tabbed sections own navigation.
The page owns vertical scrolling. Native form stacks and expanders own content;
no nested fixed-height scroll shells or custom pixel dimensions are introduced.
Evidence metadata uses labeled values. Long hashes and commands use copyable code
elements; primary prose and excerpts must wrap on narrow viewports.

## 5. Components

- Work browser and metadata search paginate at 25 records. Details and images
  load only after the reader selects the labeled control inside a work card.
  This keeps closed cards from decoding images on unrelated form submissions.
- Evidence summary: heading, caption, labeled recorded counts, source identity,
  unresolved-image warning and explicit verification boundary. States: absent,
  malformed, available and internally inconsistent manifest. No absent state
  renders zero as a verified count.
- Recovered search: labeled form, scope/mode/plane controls, submit, bounded
  results and source labels. States: initial, empty input, loading, primary,
  exploratory, no results, absent index and integrity error. Primary is default.
- Result: source title, edition/locator, role and plane, literal excerpt, rights
  statement and source URL. Complete private passage bodies are not displayed.
- Version caption: package version, methods profile and dashboard schema. These
  are software contracts, separate from corpus completeness and archived papers.

## 6. Motion and interaction

Use native keyboard, focus, hover, pressed, disabled and form-submit behavior.
Search runs on explicit submission; no network request or index build runs on
page load. Show a native progress indicator while validating and searching.
Errors appear beside the relevant search. No custom animation or motion.

## 7. Depth and surface

Use native theme surface separation and expanders. No application shadows,
decorative accent stripes, custom radii or extra card surfaces are added.

The existing generated HTML workbench retains its own palette (`--ink`, `--muted`,
`--line`, `--bg`, `--panel`, `--slate`) and system-font header/body hierarchy from
`blake/corpus/visualizations.py`. Version metadata uses the existing header
paragraph primitive. This update introduces no HTML styling tokens.

## 8. Accessibility constraints and verification limits

All new inputs require visible labels and keyboard access. Scope distinctions
must be stated in words. Excerpts are literal text. Verify empty, damaged,
primary and exploratory states with real data; inspect narrow and wide renders.
Native framework behavior is retained, not certified as a new application-wide
accessibility or Lighthouse audit. Existing views are outside the visual redesign
scope; findings in a changed flow must be fixed and rechecked before release.


## 9. Shared offline search workspace

The separate `blake.methods.workspace` HTML workspace is an offline artifact,
not a replacement for the Streamlit interface above. Its shared CSS defines its
own typography, colors, spacing, controls and responsive layout. Application
adapters may supply HTML/CSS and explicit escaped title, brand and footer labels;
the JavaScript matcher remains a single shared resource. The public template uses
neutral corpus language, while private applications own their branding.

Search submission shows busy, error, empty and populated states. Returned-hit
caps and twenty-hit pages limit display only; distribution facets retain complete
counts and eligible zero-hit groups. Every shown hit retains its source URL,
rights, edition, locator, text hash and original-codepoint span. Full texts are
embedded in the private artifact, so that artifact is not a public export.

The renderer emits inert JSON and hash-bound script/style CSP declarations,
with runtime network connections disabled. It carries Python-produced Unicode
folding, whitespace and word-membership tables for browser parity. Native focus,
labels, skip navigation, live status and pagination remain part of the template.
These implementation contracts do not constitute an accessibility certification;
installed-resource checks and rendered browser inspection remain separate gates.
