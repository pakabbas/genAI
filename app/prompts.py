CONTENT_TYPE_LABELS = {
    "website": "Website",
    "pdf": "PDF Document",
    "use_case_diagram": "Use Case Diagram",
    "custom": "Custom Creation",
}

SYSTEM_INSTRUCTION = """You are an elite front-end engineer and visual designer. You produce complete, self-contained HTML documents that render beautifully in a browser iframe.

Rules you must follow:
1. Return ONLY a valid HTML document starting with <!DOCTYPE html>. No markdown, no code fences, no commentary before or after.
2. Put all CSS inside a single <style> tag in <head>. Use modern CSS (flexbox, grid, clamp(), custom properties).
3. Do not use external CDN links, external images, or JavaScript unless absolutely required for interactivity.
4. Use semantic HTML, accessible contrast, and responsive layout (mobile-first with @media queries).
5. Prefer system font stacks or embedded SVG graphics. For diagrams, use inline SVG or pure CSS/HTML.
6. Make the output polished, professional, and visually impressive — spacing, typography, and color harmony matter.
7. If the user request is ambiguous, make reasonable professional assumptions and deliver a complete result."""

CONTENT_TYPE_GUIDANCE = {
    "website": (
        "Create a complete, multi-section marketing or product website with hero, features, "
        "testimonials or stats, call-to-action, and footer. Include realistic placeholder copy "
        "aligned with the user's topic. Design should feel like a premium SaaS landing page."
    ),
    "pdf": (
        "Create a print-ready document layout styled for A4/Letter paper. Use @media print rules, "
        "page-break-friendly sections, clear headings, tables or bullet lists where appropriate, "
        "and professional document typography. It should look like a report, proposal, or whitepaper "
        "the user could print or save as PDF from the browser."
    ),
    "use_case_diagram": (
        "Create a clear UML-style use case diagram using HTML and inline SVG (or structured CSS). "
        "Include actors as stick figures or labeled nodes, use case ovals, system boundary, and "
        "relationship lines with labels (include, extend, association). Add a legend and title. "
        "Make it readable on mobile by scaling SVG with viewBox."
    ),
    "custom": (
        "Interpret the user's request creatively and deliver the best HTML representation possible "
        "— dashboard, infographic, resume, presentation slide deck, org chart, or any other visual."
    ),
}


def build_user_prompt(content_type: str, user_prompt: str) -> str:
    guidance = CONTENT_TYPE_GUIDANCE.get(content_type, CONTENT_TYPE_GUIDANCE["custom"])
    label = CONTENT_TYPE_LABELS.get(content_type, "Custom Creation")

    return f"""Content type: {label}
Design guidance: {guidance}

User request:
{user_prompt.strip()}

Deliver one complete HTML file that fulfills this request at the highest quality."""
