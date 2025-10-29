# app.py (static-hosting mode for Railway or any host)
from flask import Flask, jsonify, send_from_directory, request
from flask_cors import CORS
from pathlib import Path
import os
import base64

app = Flask(__name__)
CORS(app, resources={r"/*": {"origins": "*"}})

BASE_DIR = Path(__file__).parent.resolve()

# Where converted or uploaded models live
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
                "name": name_only,
                "relativePath": rel,
                "buffer": b64
            })
    return jsonify(out)


@app.post("/api/uploadModel")
def upload_model():
    """
    Accepts multipart/form-data with multiple files.
    Saves them to uploads/<folder_name>_mtk/, preserving folder structure.
    """
    if "files" not in request.files:
        return jsonify({"error": "No files part in request"}), 400

    uploaded_files = request.files.getlist("files")
    if not uploaded_files:
        return jsonify({"error": "No files uploaded"}), 400

    # Infer model name from first file path or default
    first_file = uploaded_files[0]
    base_name = Path(first_file.filename).parts[0] if "/" in first_file.filename else "uploaded_model"
    model_folder = f"{base_name}_mtk"
    target_dir = UPLOAD_FOLDER / model_folder
    target_dir.mkdir(parents=True, exist_ok=True)

    # Save each uploaded file, preserving relative structure
    for file in uploaded_files:
        relative_path = Path(file.filename)
        save_path = target_dir / relative_path
        save_path.parent.mkdir(parents=True, exist_ok=True)
        file.save(save_path)

    return jsonify({
        "status": "success",
        "message": f"Model '{model_folder}' uploaded successfully.",
        "modelName": model_folder
    })


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
