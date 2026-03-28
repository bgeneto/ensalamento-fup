"""Helpers for triggering browser downloads from Streamlit in a single click."""

from __future__ import annotations

import base64
import json

import streamlit.components.v1 as components


def build_auto_download_html(
    data: bytes,
    filename: str,
    mime: str = "application/octet-stream",
) -> str:
    """Build iframe HTML that downloads the provided file payload on render."""
    encoded_payload = base64.b64encode(data).decode("utf-8")

    return f"""
<!DOCTYPE html>
<html>
  <body>
    <script>
      (() => {{
        const encodedPayload = {json.dumps(encoded_payload)};
        const mimeType = {json.dumps(mime)};
        const downloadFilename = {json.dumps(filename)};
        const binary = window.atob(encodedPayload);
        const bytes = new Uint8Array(binary.length);

        for (let index = 0; index < binary.length; index += 1) {{
          bytes[index] = binary.charCodeAt(index);
        }}

        const blob = new Blob([bytes], {{ type: mimeType }});
        const downloadUrl = URL.createObjectURL(blob);
        const link = document.createElement("a");
        link.href = downloadUrl;
        link.download = downloadFilename;
        document.body.appendChild(link);
        link.click();
        link.remove();

        window.setTimeout(() => URL.revokeObjectURL(downloadUrl), 1000);
      }})();
    </script>
  </body>
</html>
"""


def trigger_auto_download(
    data: bytes,
    filename: str,
    mime: str = "application/octet-stream",
) -> None:
    """Render a zero-height iframe that starts a browser download."""
    components.html(
        build_auto_download_html(data=data, filename=filename, mime=mime),
        height=0,
        tab_index=-1,
    )
