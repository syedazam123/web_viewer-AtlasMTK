from flask import Flask, render_template, request, send_from_directory, jsonify, send_file
from flask_cors import CORS
import subprocess
from pathlib import Path
import os
import base64

app = Flask(__name__)

# ✅ Allow CORS for any frontend (Loveable, localhost, etc.)
CORS(app, resources={r"/*": {"origins": "*"}})

# -------------------------------------------------------------------
# ✅ Folder configuration
# -------------------------------------------------------------------
BASE_DIR = Path(__file__).parent.resolve()
UPLOAD_FOLDER = BASE_DIR / "uploads"
UPLOAD_FOLDER.mkdir(parents=True, exist_ok=True)
app.config["UPLOAD_FOLDER"] = str(UPLOAD_FOLDER)

# -------------------------------------------------------------------
# ✅ Script paths
# -------------------------------------------------------------------
PYTHON_EXE = r"C:\MTK\python_pilot\.venv\Scripts\python.exe"
FEATURE_SCRIPT = r"C:\MTK\python\machining\feature_recognizer\feature_from_path.py"
DFM_SCRIPT = r"C:\MTK\python\machining\dfm_analyzer\dfm_from_path.py"
CONVERTER_SCRIPT = r"C:\MTK\python\MTKConverter\MTKConverter.py"

# -------------------------------------------------------------------
# ✅ Homepage
# -------------------------------------------------------------------
@app.route('/')
def index():
    return render_template('index.html')

# -------------------------------------------------------------------
# ✅ Analyze Endpoint
# -------------------------------------------------------------------
@app.route('/analyze', methods=['POST'])
def analyze():
    file = request.files.get('cad_file')
    if not file:
        return "No file uploaded", 400

    save_path = (UPLOAD_FOLDER / file.filename).resolve()
    file.save(str(save_path))
    stem = save_path.stem

    converted_folder = str(save_path)
    for ext in [".stp", ".STP", ".step", ".STEP"]:
        if str(save_path).lower().endswith(ext.lower()):
            converted_folder = str(save_path)[: -len(ext)] + "_mtk"
            break

    # --- Run MTK Converter ---
    try:
        converter_out = subprocess.check_output([
            PYTHON_EXE, CONVERTER_SCRIPT,
            "-i", str(save_path),
            "-p", "machining_milling",
            "-e", converted_folder
        ], text=True, stderr=subprocess.STDOUT)
    except subprocess.CalledProcessError as e:
        converter_out = f"[MTK Converter error]\n{e.output}"

    # --- Run Feature & DFM (optional) ---
    try:
        features_out = subprocess.check_output(
            [PYTHON_EXE, FEATURE_SCRIPT, str(save_path)],
            text=True, stderr=subprocess.STDOUT
        )
    except subprocess.CalledProcessError as e:
        features_out = f"[Feature recognizer error]\n{e.output}"

    try:
        dfm_out = subprocess.check_output(
            [PYTHON_EXE, DFM_SCRIPT, str(save_path)],
            text=True, stderr=subprocess.STDOUT
        )
    except subprocess.CalledProcessError as e:
        dfm_out = f"[DFM error]\n{e.output}"

    process = "machining_milling"
    model_name = Path(save_path).stem
    viewer_url = (
        f"http://localhost:5173/mtk-explorer/viewer/{process}/{model_name}"
        f"?server=http://127.0.0.1:5000/uploads/{model_name}_mtk"
    )

    html = f"""
    <h2>Analysis complete for: {file.filename}</h2>
    <h3>MTK Converter Output</h3>
    <pre style="white-space: pre-wrap;">{converter_out}</pre>
    <h3>Feature Recognition</h3>
    <pre style="white-space: pre-wrap;">{features_out}</pre>
    <h3>DFM Analysis</h3>
    <pre style="white-space: pre-wrap;">{dfm_out}</pre>
    <p><strong>Converted model folder:</strong> {converted_folder}</p>
    <p>
        <a href="{viewer_url}" target="_blank"
           style="padding:10px 15px; background-color:#007BFF; color:white;
           text-decoration:none; border-radius:5px;">
           🔍 Open in 3D Viewer
        </a>
    </p>
    <p><a href="/">Analyze another file</a></p>
    """
    return html

# -------------------------------------------------------------------
# ✅ Serve model data and manifest (fixed path & MIME)
# -------------------------------------------------------------------
@app.route("/uploads/<path:subpath>")
def serve_uploads(subpath):
    full_path = os.path.join(app.config["UPLOAD_FOLDER"], subpath)
    folder = os.path.dirname(full_path)
    file = os.path.basename(full_path)

    # --- If the viewer requests process_data.json ---
    if file == "process_data.json":
        model_name = Path(folder).name.replace("_mtk", "")
        mtkweb_dir = None

        for item in os.listdir(folder):
            if item.endswith(".mtkweb"):
                mtkweb_dir = item
                break

        if not mtkweb_dir:
            return jsonify({"error": "No .mtkweb folder found"}), 404

        # ✅ FIXED: Point to actual scenegraph.mtkweb file
        scenegraph_path = f"http://127.0.0.1:5000/uploads/{model_name}_mtk/{mtkweb_dir}/scenegraph.mtkweb"

        manifest = {
            "version": "1",
            "parts": [
                {
                    "partId": model_name,
                    "files": [
                        {"type": "mtkweb", "path": scenegraph_path}
                    ]
                }
            ]
        }

        print(f"📁 Folders inside {folder} : {os.listdir(folder)}")
        print(f"📦 Generated manifest for {model_name}: {scenegraph_path}")
        print(f"🧩 Manifest JSON: {manifest}")
        return jsonify(manifest)

    # --- Regular file serving ---
    if not os.path.exists(full_path):
        return jsonify({"error": f"File not found: {subpath}"}), 404

    if file.endswith(".json"):
        return send_file(full_path, mimetype="application/json")
    return send_from_directory(folder, file)

# -------------------------------------------------------------------
# ✅ NEW: getAllFiles endpoint (Flask equivalent of NodeJS config.ts)
# -------------------------------------------------------------------
@app.route("/api/getAllFiles", methods=["GET"])
def get_all_files():
    """
    Mimics the NodeJS getAllFiles() behavior:
    Recursively reads all files in a given folder and returns their
    relative paths and base64-encoded contents.
    """
    folder = request.args.get("folder")
    if not folder:
        return jsonify({"error": "Missing 'folder' query parameter"}), 400

    base_dir = os.path.join(app.config["UPLOAD_FOLDER"], folder)
    if not os.path.exists(base_dir):
        return jsonify({"error": f"Folder not found: {base_dir}"}), 404

    file_data = []
    for root, _, files in os.walk(base_dir):
        for fname in files:
            full_path = os.path.join(root, fname)
            rel_path = os.path.relpath(full_path, base_dir).replace("\\", "/")
            with open(full_path, "rb") as f:
                encoded = base64.b64encode(f.read()).decode("utf-8")
            file_data.append({
                "name": fname,
                "relativePath": rel_path,
                "buffer": encoded
            })

    print(f"📦 getAllFiles served {len(file_data)} files from {base_dir}")
    return jsonify(file_data)

# -------------------------------------------------------------------
# ✅ Run Flask (Docker/Railway compatible)
# -------------------------------------------------------------------
if __name__ == "__main__":
    print("🚀 Flask server running with full CORS enabled...")
    app.run(host="0.0.0.0", port=int(os.getenv("PORT", 5000)), debug=True)
