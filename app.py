
from flask import Flask
from markupsafe import escape
import boto3

app = Flask(__name__)

s3 = boto3.client("s3")
BUCKET = "amz-data-ibero-1-2026-c5"

@app.route("/")
def listar_archivos():
    try:
        archivos = []
        paginator = s3.get_paginator("list_objects_v2")

        for pagina in paginator.paginate(Bucket=BUCKET):
            for obj in pagina.get("Contents", []):
                archivos.append(
                    f"<li>{escape(obj['Key'])}</li>"
                )

        if not archivos:
            return "<h2>El bucket está vacío</h2>"

        return (
            "<h1>Archivos almacenados en S3</h1>"
            + "<ul>"
            + "".join(archivos)
            + "</ul>"
        )

    except Exception:
        app.logger.exception("Error consultando S3")
        return "Error al consultar S3. Revisar logs.", 500

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000)
    