#!/usr/bin/env python3
"""Tiny static file server for the build folder, so the Ardens web emulator can
fetch the freshly built .hex / .bin from this machine (needs CORS headers)."""
import http.server, os, sys


class Handler(http.server.SimpleHTTPRequestHandler):
    def end_headers(self):
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Private-Network", "true")
        self.send_header("Cache-Control", "no-store")
        super().end_headers()

    def do_OPTIONS(self):
        self.send_response(204)
        self.send_header("Access-Control-Allow-Methods", "GET, OPTIONS")
        self.send_header("Access-Control-Allow-Headers", "*")
        self.end_headers()


if __name__ == "__main__":
    root = sys.argv[1] if len(sys.argv) > 1 else "."
    port = int(sys.argv[2]) if len(sys.argv) > 2 else 8642
    os.chdir(root)
    http.server.ThreadingHTTPServer(("127.0.0.1", port), Handler).serve_forever()
