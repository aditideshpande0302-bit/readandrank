"""Combine the individual screen files into one clickable prototype (index.html).

Emits a complete HTML document. Each screen's CSS is scoped to its own container so shared class names
(.race, .btn, h1, ...) don't collide. Run: python3 build_flow.py
"""
import re
from pathlib import Path

HERE = Path(__file__).parent
SCREENS = [("landing", "landing.html"), ("issues", "issues.html"), ("read", "read.html"), ("ballot", "ballot.html"), ("browse", "browse.html"), ("compass", "compass.html"), ("stances", "stances.html"), ("ready", "ready.html")]
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
    """Prefix every rule with the scope. Handles nested @media; leaves @keyframes alone."""
    out, stack, buf = [], [], ""
    for ch in css:
        if ch == "{":
            # Drop comments so a rule like "/* note */ :root {" is still seen as :root.
            buf = re.sub(r"/\*.*?\*/", "", buf, flags=re.S)
            head = buf.strip()
            in_keyframes = any(h.startswith("@keyframes") for h in stack)
            if head.startswith("@") or in_keyframes or (not stack and head.startswith(":root")):
                out.append(buf + "{")
            else:
                out.append(buf[: len(buf) - len(buf.lstrip())] + scope_selectors(head, scope) + " {")
            stack.append(head)
            buf = ""
        elif ch == "}":
            out.append(buf + "}")
            if stack:
                stack.pop()
            buf = ""
        else:
            buf += ch
    out.append(buf)
    return "".join(out)


def main():
    styles, bodies, scripts = [], [], []
    head = None
    for name, file in SCREENS:
        src = (HERE / file).read_text(encoding="utf-8")
        if head is None:
            head = "".join(re.findall(r"<link[^>]*>\n?", src))
        style, body, script = split(src)
        styles.append(scope_css(style, f"#s-{name}"))
        hidden = "" if name == "landing" else " hidden"
        bodies.append(f'<div class="screen" id="s-{name}"{hidden}>\n{body}\n</div>')
        scripts.append(f"<script>{script}</script>")

    router = """<script>
  (function () {
    var screens = {};
    document.querySelectorAll('.screen').forEach(function (el) { screens[el.id.slice(2)] = el; });
    var active = 'landing', activeView = 'landing';
    // Views that reuse another screen: the results page for someone who already has a compass.
    var ALIAS = { 'ballot-compass': 'ballot' };
    function go(target) {
      var name = ALIAS[target] || target;
      name = screens[name] && name !== 'landing' ? name : 'landing';
      var view = ALIAS[target] ? target : name;
      var changed = view !== activeView, prev = active;
      Object.keys(screens).forEach(function (k) { screens[k].hidden = k !== name; });
      active = name; activeView = view;
      var anchor = name === 'landing' && target && target !== 'top' && document.getElementById(target);
      if (anchor) anchor.scrollIntoView({ block: 'start' });
      else if (changed || target === 'top') window.scrollTo(0, 0);
      if (changed) {
        if (screens[prev]) screens[prev].dispatchEvent(new CustomEvent('screen:hide'));
        screens[name].dispatchEvent(new CustomEvent('screen:show', { detail: { from: prev, view: view } }));
        var h = screens[name].querySelector('h1, h2');
        if (h) { h.setAttribute('tabindex', '-1'); h.focus({ preventScroll: true }); }
      }
      try { history.replaceState(null, '', name === 'landing' ? location.pathname + location.search : '#' + view); } catch (err) {}
    }
    document.addEventListener('click', function (e) {
      var a = e.target.closest('a[href^="#"]');
      if (!a) return;
      e.preventDefault();
      var target = a.getAttribute('href').slice(1);
      if (target) go(target);
    });
    // "Start reading" on the issues screen opens the reading screen.
    document.addEventListener('submit', function (e) {
      if (e.target.id === 'issues-form') go('read');
    });
    window.RRGo = go;
    var initial = location.hash.slice(1);
    if (screens[initial] || ALIAS[initial]) go(initial);
  })();
</script>"""

    out = (
        "<!doctype html>\n"
        '<html lang="en">\n'
        "<head>\n"
        '<meta charset="utf-8">\n'
        '<meta name="viewport" content="width=device-width, initial-scale=1, viewport-fit=cover">\n'
        "<title>Read &amp; Rank Prototype</title>\n"
        + head
        + "<style>\n"
        + "\n".join(styles)
        + "\n.screen { flex: 1 0 auto; display: flex; flex-direction: column; }"
        + "\n.screen[hidden] { display: none; }"
        + "\n.screen [tabindex=\"-1\"]:focus, .screen [tabindex=\"-1\"]:focus-visible { outline: none !important; }"
        + "\n</style>\n"
        + "</head>\n<body>\n\n"
        + "\n\n".join(bodies)
        + "\n\n"
        + "\n".join(scripts)
        + "\n"
        + router
        + "\n"
        + "</body>\n</html>\n"
    )
    (HERE / "index.html").write_text(out, encoding="utf-8")
    print("wrote index.html")


if __name__ == "__main__":
    main()
