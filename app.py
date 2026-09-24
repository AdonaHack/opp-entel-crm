from datetime import datetime, timedelta
from flask import Flask, jsonify, render_template, request
import gspread
from oauth2client.service_account import ServiceAccountCredentials

app = Flask(__name__)


# --- CONEXIÓN CON GOOGLE SHEETS ---
def get_sheet():
  scope = [
      "https://spreadsheets.google.com/feeds",
      "https://www.googleapis.com/auth/drive",
  ]
  creds = ServiceAccountCredentials.from_json_keyfile_name(
      "service_account.json", scope
  )
  client = gspread.authorize(creds)
  return client.open("OPP RUC10 ENTEL EMPRESAS").worksheet("OPP RUC10")


@app.route("/")
def home():
  return render_template("index.html")


# Ruta para verificar si el RUC está libre o reservado
@app.route("/verificar", methods=["POST"])
def verificar_ruc():
  data = request.get_json()
  ruc = data.get("ruc", "").strip()

  if len(ruc) != 11 or not ruc.startswith("10"):
    return jsonify({
        "status": "error",
        "message": (
            "El RUC debe tener 11 dígitos y comenzar estrictamente con '10'."
        ),
    })

  try:
    sheet = get_sheet()
    rows = sheet.get_all_records()
    hoy = datetime.now()

    for row in rows:
      if str(row.get("NUMERO DE RUC")) == ruc:
        fecha_venc_str = row.get("FECHA VENCIMIENTO")
        if fecha_venc_str:
          fecha_venc = datetime.strptime(
              fecha_venc_str.split(" ")[0], "%Y-%m-%d"
          )
          if fecha_venc >= hoy and row.get("ESTADO") == "ACTIVA":
            return jsonify({
                "status": "ocupado",
                "dealer": row.get("DEALER"),
                "vencimiento": fecha_venc_str,
            })

    return jsonify({"status": "libre"})
  except Exception as e:
    return jsonify({"status": "error", "message": str(e)})


# Ruta para registrar la OPP en Google Sheets
@app.route("/registrar", methods=["POST"])
def registrar_opp():
  datos = request.get_json()
  try:
    sheet = get_sheet()
    marca_temporal = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    fecha_vencimiento = (datetime.now() + timedelta(days=7)).strftime(
        "%Y-%m-%d %H:%M:%S"
    )

    nueva_fila = [
        marca_temporal,
        datos.get("ruc"),
        datos.get("direccion").upper(),
        datos.get("distrito"),
        datos.get("ejecutivo").upper(),
        datos.get("dealer"),
        "ACTIVA",
        fecha_vencimiento,
    ]

    sheet.append_row(nueva_fila)
    return jsonify({"status": "success"})
  except Exception as e:
    return jsonify({"status": "error", "message": str(e)})


if __name__ == "__main__":
  app.run(debug=True, port=5000)