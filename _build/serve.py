"""Local preview of the built site: python3 serve.py [port]. Serves _build/site with GitHub Pages' /x -> x.html rule."""
import functools, http.server, os, sys

ROOT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "site")


class H(http.server.SimpleHTTPRequestHandler):
    def translate_path(self, path):
        p = super().translate_path(path)
        if not os.path.exists(p) and os.path.exists(p + ".html"):
            return p + ".html"
        return p

    def send_error(self, code, message=None, explain=None):
        nf = os.path.join(ROOT, "404.html")
        if code == 404 and os.path.exists(nf):
            body = open(nf, "rb").read()
            self.send_response(404)
            self.send_header("Content-Type", "text/html; charset=utf-8")
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)
            return
        super().send_error(code, message, explain)

    def log_message(self, *a):
        pass


def serve(port=8765):
    httpd = http.server.ThreadingHTTPServer(("127.0.0.1", port), functools.partial(H, directory=ROOT))
    return httpd


if __name__ == "__main__":
    serve(int(sys.argv[1]) if len(sys.argv) > 1 else 8765).serve_forever()
