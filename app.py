# app.py (static-hosting mode for Railway or any host)
from flask import Flask, jsonify, send_from_directory, request
from flask_cors import CORS
from pathlib import Path
import os
import base64

app = Flask(__name__)
CORS(app, resources={r"/*": {"origins": "*"}})

BASE_DIR = Path(__file__).parent.resolve()

# Where converted models live (each model: <name>_mtk with <name>.mtkweb inside)
UPLOAD_FOLDER = BASE_DIR / "uploads"
UPLOAD_FOLDER.mkdir(parents=True, exist_ok=True)

@app.get("/health")
def health():
    return "ok", 200

@app.get("/")
def index():
    return "MTK static host is running. Try /api/listModels", 200

@app.get("/api/listModels")
def list_models():
    """Lists folders immediately inside /uploads that end with _mtk."""
    results = []
    if UPLOAD_FOLDER.exists():
        for child in sorted(UPLOAD_FOLDER.iterdir()):
            if child.is_dir() and child.name.endswith("_mtk"):
                results.append(child.name)
    return jsonify({"models": results})


@app.get("/api/getAllFiles")
def get_all_files():
    """
    Returns every file in a given converted folder as base64.
    Usage: /api/getAllFiles?folder=<model_name>_mtk
    Response: [ { name, relativePath, buffer(base64) }, ... ]
    """
    folder = request.args.get("folder", "").strip()
    if not folder:
        return jsonify({"error": "Missing ?folder=<name>_mtk"}), 400

    target = (UPLOAD_FOLDER / folder).resolve()
    if not target.exists() or not target.is_dir():
        return jsonify({"error": f"Folder not found: {folder}"}), 404

    out = []
    for root, _, files in os.walk(target):
        for f in files:
            full = Path(root) / f
            rel = str(full.relative_to(target)).replace("\\", "/")
            name_only = rel.split("/")[-1]
            with open(full, "rb") as fh:
                b64 = base64.b64encode(fh.read()).decode("ascii")
            out.append({
                "name": name_only,       # filename only
                "relativePath": rel,     # e.g., barrel.mtkweb/scenegraph.mtkweb
                "buffer": b64            # base64 content
            })
    return jsonify(out)


@app.post("/analyze")
def analyze():
    """
    Placeholder analyze endpoint for Loveable uploads.
    It simply acknowledges the request and returns mock data.
    (Full conversion not available in Railway due to MTK licensing limits.)
    """
    file = request.files.get("file")
    if not file:
        return jsonify({"error": "No file uploaded"}), 400

    # For now, just return a dummy folder name.
    filename = file.filename.rsplit(".", 1)[0]
    result_folder = f"{filename}_mtk"
    return jsonify({
        "status": "success",
        "message": "Analysis placeholder executed successfully.",
        "converted_folder": result_folder
    })


@app.get("/uploads/<path:subpath>")
def serve_uploads(subpath):
    """Optional direct file serving for images/thumbs."""
    full_path = (UPLOAD_FOLDER / subpath).resolve()
    if not full_path.exists() or not full_path.is_file():
        return jsonify({"error": f"Not found: {subpath}"}), 404
    return send_from_directory(directory=str(full_path.parent), path=full_path.name)


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.getenv("PORT", 5000)))
