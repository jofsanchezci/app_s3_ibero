# Laboratorio: Integración de Amazon EC2 con Amazon S3

**Curso:** Computación en la Nube y Big Data  
**Semana:** 4 — Servicio Amazon S3  
**Duración estimada:** 25–30 minutos  
**Modalidad:** Demostración guiada y práctica

## 1. Objetivo

Implementar una aplicación web en una instancia **Amazon EC2** que consulte y muestre los nombres de archivos almacenados en un **bucket Amazon S3**, utilizando **Python, Flask y Boto3**. Reconocer el papel de **IAM** en la autorización del acceso.

## 2. Arquitectura

```text
Usuario (navegador)
        |
        | HTTP :5000
        v
Amazon EC2 (Flask + Boto3)
        |
        | Solicitud a la API de S3 con credenciales del rol IAM
        v
Amazon S3 (bucket: datos.csv, imagen.jpg, documento.pdf)
```

> **Nota:** IAM no es un servidor intermediario por el que pasan los archivos; el rol proporciona credenciales temporales y permisos a EC2. No es necesario crear una VPN. EC2 necesita conectividad al endpoint de S3 mediante Internet/NAT o un endpoint de VPC para S3.

## 3. Requisitos previos

- Acceso a una cuenta o laboratorio de AWS con permisos para usar EC2 y S3.
- Una instancia EC2 con Amazon Linux y acceso por SSH o EC2 Instance Connect.
- Un rol IAM **existente y autorizado** para EC2 con `s3:ListBucket` sobre el bucket. Para descargar objetos se requiere además `s3:GetObject`.
- Acceso de red desde EC2 a Amazon S3.
- Puerto TCP 5000 habilitado **solo desde la IP del docente o estudiantes que realizarán la prueba**. El puerto 22, si se usa SSH, también debe restringirse a las IP autorizadas.

En **AWS Academy/Vocareum**, el usuario estudiante puede no tener `iam:CreateRole` ni `iam:PassRole`. Si el laboratorio dispone de `LabRole` u otro rol autorizado, úselo; si no, solicite al administrador habilitar una opción. No intente eludir las restricciones del laboratorio.

## 4. Procedimiento

### Paso 1. Crear el bucket S3 (5 minutos)

1. Abrir **AWS Console → S3 → Create bucket**.
2. Escribir un nombre globalmente único y seleccionar la región.
3. Mantener el bloqueo de acceso público habilitado para esta práctica.
4. Crear el bucket y cargar tres archivos de prueba: `datos.csv`, `imagen.jpg`, `documento.pdf`.
5. Copiar el nombre exacto del bucket.

### Paso 2. Preparar EC2 (5 minutos)

1. Ir a **EC2 → Launch instance** y seleccionar Amazon Linux (por ejemplo, una instancia pequeña admitida por el laboratorio).
2. Configurar acceso mediante SSH o EC2 Instance Connect.
3. En el **Security Group**, permitir TCP 5000 desde la IP de prueba; si se necesita SSH, permitir TCP 22 desde una IP autorizada.
4. Confirmar que la instancia tenga conectividad a S3 y una dirección pública si se accederá a Flask desde el navegador externo.
5. Conectarse a la instancia.

### Paso 3. Asociar el rol IAM (5 minutos)

En la consola:

**EC2 → Instances → seleccionar instancia → Actions → Security → Modify IAM Role**.

Seleccionar un rol existente que el laboratorio permita asociar, por ejemplo `LabRole` **solo si está disponible y tiene permisos adecuados**. Confirmar la modificación.

En la terminal de EC2:

```bash
aws sts get-caller-identity
aws s3 ls s3://nombre-del-bucket
```

Reemplazar `nombre-del-bucket` por el nombre real. Si el segundo comando muestra los archivos, la lectura de la lista está autorizada. `get-caller-identity` verifica la identidad, pero **no demuestra por sí solo que exista permiso para S3**.

### Paso 4. Instalar dependencias (3 minutos)

En Amazon Linux 2023:

```bash
sudo dnf install -y python3
mkdir -p ~/demo-s3
cd ~/demo-s3
python3 -m venv venv
source venv/bin/activate
pip install flask boto3
```

Si AWS CLI no está disponible, instálelo siguiendo la documentación de AWS correspondiente a su distribución.

### Paso 5. Crear la aplicación Flask (5 minutos)

Guardar el siguiente código en `app.py` y reemplazar el nombre del bucket:

```python
from flask import Flask
from markupsafe import escape
from botocore.exceptions import ClientError
import boto3

app = Flask(__name__)
s3 = boto3.client("s3")
BUCKET = "nombre-del-bucket"

@app.route("/")
def listar_archivos():
    try:
        archivos = []
        paginator = s3.get_paginator("list_objects_v2")
        for pagina in paginator.paginate(Bucket=BUCKET):
            for obj in pagina.get("Contents", []):
                archivos.append(f"<li>{escape(obj['Key'])}</li>")

        if not archivos:
            return "<h2>El bucket está vacío</h2>"

        return (
            "<h1>Archivos almacenados en S3</h1>"
            + "<ul>" + "".join(archivos) + "</ul>"
        )
    except ClientError:
        app.logger.exception("Error de acceso a S3")
        return "Error al consultar S3. Revise los permisos y los registros.", 500
    except Exception:
        app.logger.exception("Error inesperado")
        return "Error interno. Revise los registros de Flask.", 500

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000, debug=False)
```

La aplicación **lista nombres de objetos**; no descarga ni muestra el contenido de los archivos. La paginación permite recorrer más de 1000 objetos.

### Paso 6. Ejecutar y comprobar (5 minutos)

```bash
source ~/demo-s3/venv/bin/activate
cd ~/demo-s3
python3 app.py
```

Abrir en el navegador:

```text
http://IP_PUBLICA_EC2:5000
```

Resultado esperado:

```text
Archivos almacenados en S3
- datos.csv
- imagen.jpg
- documento.pdf
```

**Seguridad:** Flask en este modo utiliza un servidor de desarrollo. Úselo solo durante la demostración y cierre el puerto 5000 al finalizar. Para producción, utilice un servidor WSGI y HTTPS.

## 5. Diagnóstico de problemas

| Síntoma | Verificación y acción |
|---|---|
| `AccessDenied` | Comprobar permisos `s3:ListBucket`, políticas del bucket y posibles restricciones del laboratorio. |
| `Unable to locate credentials` | Verificar que el rol esté asociado a EC2 y que Boto3/AWS CLI pueda obtener credenciales temporales. |
| `Internal Server Error` | Revisar la salida de la terminal donde se ejecuta Flask. |
| No carga la página | Comprobar IP pública, puerto 5000, Security Group, rutas y proceso Flask. |
| No aparecen objetos | Verificar el nombre del bucket y que se hayan cargado archivos. |
| `iam:CreateRole` denegado | Utilizar un rol preexistente autorizado o solicitar apoyo al administrador del laboratorio. |

> La prueba `aws s3 ls s3://nombre-del-bucket` ayuda a aislar problemas de IAM o conectividad antes de ejecutar Flask.

## 6. Actividad para los estudiantes

1. Subir un nuevo archivo CSV al bucket y actualizar la página para comprobar que aparece.
2. Modificar `app.py` para mostrar el **tamaño en bytes** de cada objeto, usando `obj['Size']`.
3. Explicar qué ocurriría si el rol de EC2 no tuviera `s3:ListBucket` (sin necesidad de modificar permisos si el laboratorio lo restringe).

**Evidencias sugeridas:** captura de la lista de archivos en S3, salida de `aws s3 ls`, captura de la página Flask y breve explicación del papel de IAM.

## 7. Conclusión

- **EC2** ejecuta la aplicación y aporta capacidad de cómputo.
- **S3** almacena los objetos independientemente de EC2.
- **IAM** autoriza las operaciones sobre los recursos de AWS.
- **Boto3** permite consultar S3 desde Python.
- **Flask** presenta la información en una página web.

Esta práctica ilustra la separación entre cómputo y almacenamiento, un principio fundamental de las arquitecturas de nube y Big Data.

## 8. Referencias

- [Amazon S3 — Documentación](https://docs.aws.amazon.com/AmazonS3/latest/userguide/Welcome.html)
- [Uso de roles IAM para instancias EC2](https://docs.aws.amazon.com/AWSEC2/latest/UserGuide/iam-roles-for-amazon-ec2.html)
- [Boto3 — S3](https://boto3.amazonaws.com/v1/documentation/api/latest/reference/services/s3.html)
- [Flask — Documentación](https://flask.palletsprojects.com/)
