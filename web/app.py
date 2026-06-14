import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "app"))

from flask import Flask, render_template, request, jsonify, send_file
from engine import analyze_symptoms, build_protocol, priority_text, analyze_ryodoraku, generate_tcm_explanation
from data.symptom_categories import CATALOG
from data.diagnoses import DIAGNOSES
from word_export import generate_word

app = Flask(__name__)

@app.route("/")
def index():
    return render_template("index.html")

@app.route("/api/catalog")
def api_catalog():
    return jsonify([{"name": n, "emoji": e, "symptoms": s} for n, e, s in CATALOG])

@app.route("/api/diagnoses")
def api_diagnoses():
    return jsonify(sorted(DIAGNOSES.keys()))

@app.route("/api/analyze", methods=["POST"])
def api_analyze():
    data = request.json
    symptoms = data.get("symptoms", [])
    acute    = data.get("acute", False)
    scores   = analyze_symptoms(symptoms)
    protocol = build_protocol(scores, acute)
    return jsonify({"scores": scores, "protocol": protocol, "priority": priority_text(scores)})

@app.route("/api/ryodoraku", methods=["POST"])
def api_ryodoraku():
    data = request.json
    values = {k: tuple(v) for k, v in data.get("values", {}).items()}
    scores, details = analyze_ryodoraku(values)
    protocol = build_protocol(scores, False)
    return jsonify({"scores": scores, "protocol": protocol,
                    "details": details, "priority": priority_text(scores)})

@app.route("/api/diagnosis/<name>")
def api_diagnosis(name):
    scores = DIAGNOSES.get(name, {})
    protocol = build_protocol(scores, False)
    return jsonify({"scores": scores, "protocol": protocol, "priority": priority_text(scores)})

@app.route("/api/word", methods=["POST"])
def api_word():
    data     = request.json
    symptoms = data.get("symptoms", [])
    acute    = data.get("acute", False)
    ryo      = data.get("ryo", {})
    diag_name= data.get("diagnosis", "")

    if ryo:
        values = {k: tuple(v) for k, v in ryo.items()}
        scores, _ = analyze_ryodoraku(values)
    elif diag_name:
        scores = DIAGNOSES.get(diag_name, {})
    else:
        scores = analyze_symptoms(symptoms)

    protocol = build_protocol(scores, acute)
    tcm_text = generate_tcm_explanation(scores, protocol, symptoms)
    buf = generate_word(scores, protocol, symptoms, tcm_text)
    return send_file(
        buf,
        mimetype="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
        as_attachment=True,
        download_name="протокол_ТКМ.docx"
    )

@app.route("/api/explain", methods=["POST"])
def api_explain():
    data      = request.json
    symptoms  = data.get("symptoms", [])
    acute     = data.get("acute", False)
    ryo       = data.get("ryo", {})
    diag_name = data.get("diagnosis", "")
    if ryo:
        values = {k: tuple(v) for k, v in ryo.items()}
        scores, _ = analyze_ryodoraku(values)
    elif diag_name:
        scores = DIAGNOSES.get(diag_name, {})
    else:
        scores = analyze_symptoms(symptoms)
    protocol = build_protocol(scores, acute)
    text = generate_tcm_explanation(scores, protocol, symptoms)
    return jsonify({"text": text})

@app.route("/api/custom", methods=["POST"])
def api_custom():
    import json as _json
    custom_path = os.path.join(os.path.dirname(__file__), "..", "app", "data", "custom_symptoms.json")
    data = request.json
    name    = data.get("name", "").strip()
    weights = data.get("weights", {})
    if not name:
        return jsonify({"error": "no name"}), 400
    try:
        with open(custom_path, encoding="utf-8") as f:
            custom = _json.load(f)
    except Exception:
        custom = {}
    custom[name] = {k: int(v) for k, v in weights.items()}
    with open(custom_path, "w", encoding="utf-8") as f:
        _json.dump(custom, f, ensure_ascii=False, indent=2)
    from engine import _ALL_SYMPTOMS
    _ALL_SYMPTOMS[name] = custom[name]
    return jsonify({"ok": True})

if __name__ == "__main__":
    import socket
    host = socket.gethostbyname(socket.gethostname())
    print(f"\n  ТКМ Акупунктура запущена!")
    print(f"  Локально:    http://localhost:5000")
    print(f"  По сети:     http://{host}:5000  (iOS / Android)\n")
    app.run(host="0.0.0.0", port=5000, debug=False)
