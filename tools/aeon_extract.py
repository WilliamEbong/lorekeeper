"""Re-extract the web app, templates and assets embedded in AeonTimeline.exe.

Aeon Timeline 3.5.123 stores its CEF web app as concatenated zlib streams inside
PE resources of custom type 256 (IDs 3000-3004). This script inflates every stream
into <out>/<resource id>/<NNNN>.bin. Output is Aeon's own content: write it to a
scratch folder, never into this repo.

Usage: python -I tools/aeon_extract.py "<path to AeonTimeline.exe>" <out_dir>
"""
import hashlib
import os
import sys
import zlib

# Offsets and sizes from REA inspect_pe_resources on this exact build.
# ponytail: hardcoded for one exe hash; for another build, rerun REA
# inspect_pe_resources and replace this table.
EXE_SHA256 = "d985701dd1dc49ea06eab3bd67c2f761de0641ec717fc1ef73aae3ccc72264e4"
RESOURCES = [  # (resource id, file offset, byte length)
    (3000, 2213008, 6496149),   # main web app: index.html, main.js, ReducerWorker, strings, images
    (3001, 8709160, 6463782),   # near-duplicate of 3000
    (3002, 15172944, 2149500),  # licensing/trial/purchase window
    (3003, 17322448, 615147),   # 17 built-in .aeon templates (+ docx attachment sample)
    (3004, 17937600, 5922400),  # sample with jpg/pdf attachments + template definitions
]


def inflate_all(buf):
    """Yield each zlib stream in buf; stop at the trailing index (non-zlib bytes)."""
    while buf[:1] == b"x":
        d = zlib.decompressobj()
        try:
            data = d.decompress(buf)
        except zlib.error:
            return
        yield data
        buf = d.unused_data


def main(exe, out):
    raw = open(exe, "rb").read()
    digest = hashlib.sha256(raw).hexdigest()
    if digest != EXE_SHA256:
        sys.exit(f"exe hash {digest} differs from the known build; refresh RESOURCES via REA inspect_pe_resources")
    for rid, off, size in RESOURCES:
        target = os.path.join(out, str(rid))
        os.makedirs(target, exist_ok=True)
        count = 0
        for i, data in enumerate(inflate_all(raw[off:off + size])):
            with open(os.path.join(target, f"{i:04d}.bin"), "wb") as f:
                f.write(data)
            count += 1
        print(rid, "streams:", count)


if __name__ == "__main__":
    if len(sys.argv) != 3:
        sys.exit(__doc__)
    main(sys.argv[1], sys.argv[2])
