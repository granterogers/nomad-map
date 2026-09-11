"""Step 8 - assemble the single self-contained page from web/ + data/bundle.json."""
import json, os, sys
sys.path.insert(0, os.path.dirname(__file__))
import common

ROOT = common.ROOT
WEB = os.path.join(ROOT, "web")
OUT = os.path.join(ROOT, "dist", "nomad-radar.html")


def main():
    parts = [open(os.path.join(WEB, f), encoding="utf-8").read()
             for f in ("head.html", "body.html")]
    js = "\n".join(open(os.path.join(WEB, f), encoding="utf-8").read()
                   for f in ("app1.js", "app2.js", "app3.js", "app4.js", "app6.js", "app5.js"))
    bundle = open(os.path.join(ROOT, "data", "bundle.json"), encoding="utf-8").read()
    # </script> can only appear inside the JSON string, so escaping the slash is safe
    bundle = bundle.replace("</", "<\\/")
    html = (parts[0] + "\n" + parts[1] +
            '\n<script id="bundle" type="application/json">' + bundle + "</script>\n" +
            "<script>\n" + js + "\n</script>\n")
    os.makedirs(os.path.dirname(OUT), exist_ok=True)
    open(OUT, "w", encoding="utf-8").write(html)
    print(f"wrote {OUT} ({os.path.getsize(OUT)/1e6:.2f} MB)")


if __name__ == "__main__":
    main()
