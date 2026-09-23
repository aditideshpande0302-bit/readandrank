"""Combine the individual screen files into one clickable prototype (index.html).

Each screen's CSS is scoped to its own container so shared class names
(.race, .btn, h1, ...) don't collide. Run: python3 build_flow.py
"""
import re
from pathlib import Path

HERE = Path(__file__).parent
SCREENS = [("landing", "landing.html"), ("issues", "issues.html")]
GLOBAL = (":root", "*", "body", "@")


def split(src):
    style = re.search(r"<style>(.*?)</style>", src, re.S).group(1)
    script = re.search(r"<script>(.*?)</script>", src, re.S).group(1)
    body = re.sub(r"<title>.*?</title>|<link[^>]*>|<style>.*?</style>|<script>.*?</script>", "", src, flags=re.S)
    return style, body.strip(), script


def scope_selectors(sel, scope):
    out = []
    for s in sel.split(","):
        s = s.strip()
        out.append(s if s.startswith(GLOBAL) else f"{scope} {s}")
    return ", ".join(out)


def scope_css(css, scope):
    """Prefix every rule with the scope; handles one level of @media nesting."""
    out, i, depth, buf = [], 0, 0, ""
    for ch in css:
        if ch == "{":
            head = buf.strip()
            if head.startswith("@") or depth == 0 and head.startswith(":root"):
                out.append(buf + "{")
            else:
                out.append(buf[: len(buf) - len(buf.lstrip())] + scope_selectors(head, scope) + " {")
            depth += 1
            buf = ""
        elif ch == "}":
            out.append(buf + "}")
            depth -= 1
            buf = ""
        else:
            buf += ch
    out.append(buf)
    return "".join(out)


def main():
    styles, bodies, scripts = [], [], []
    head = None
    for name, file in SCREENS:
        src = (HERE / file).read_text()
        if head is None:
            head = "".join(re.findall(r"<link[^>]*>\n?", src))
        style, body, script = split(src)
        styles.append(scope_css(style, f"#s-{name}"))
        hidden = "" if name == "landing" else " hidden"
        bodies.append(f'<div class="screen" id="s-{name}"{hidden}>\n{body}\n</div>')
        scripts.append(f"<script>{script}</script>")

    router = """<script>
  (function () {
    var screens = { landing: document.getElementById('s-landing'), issues: document.getElementById('s-issues') };
    function current() { return screens.issues.hidden ? 'landing' : 'issues'; }
    function go(target) {
      var name = target === 'issues' ? 'issues' : 'landing';
      var changed = name !== current();
      screens.landing.hidden = name !== 'landing';
      screens.issues.hidden = name !== 'issues';
      var anchor = name === 'landing' && target && target !== 'top' && document.getElementById(target);
      if (anchor) anchor.scrollIntoView({ block: 'start' });
      else if (changed || target === 'top') window.scrollTo(0, 0);
      if (changed) { var h = screens[name].querySelector('h1, h2'); if (h) { h.setAttribute('tabindex', '-1'); h.focus({ preventScroll: true }); } }
    }
    document.addEventListener('click', function (e) {
      var a = e.target.closest('a[href^="#"]');
      if (!a) return;
      e.preventDefault();
      var target = a.getAttribute('href').slice(1);
      if (target) go(target);
      try { history.replaceState(null, '', target === 'issues' ? '#issues' : location.pathname + location.search); } catch (err) {}
    });
    if (location.hash === '#issues') go('issues');
  })();
</script>"""

    out = (
        "<title>Read &amp; Rank Prototype</title>\n"
        + head
        + "<style>\n"
        + "\n".join(styles)
        + "\n</style>\n\n"
        + "\n\n".join(bodies)
        + "\n\n"
        + "\n".join(scripts)
        + "\n"
        + router
        + "\n"
    )
    (HERE / "index.html").write_text(out)
    print("wrote index.html")


if __name__ == "__main__":
    main()
