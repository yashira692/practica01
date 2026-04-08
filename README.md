
# Caso 2 - Consulta ONPE con Docker

El programa:

lee una lista de DNIs consulta el portal ONPE verifica si es miembro de mesa genera un Excel con los resultados

Estructura del proyecto:
app/
  main.py
  input_dnis.csv
  requirements.txt
  chromedriver.exe
output/
Dockerfile
Dockerfile.optimizado
Dockerfile.multistage
README.md
.dockerignore


Instalación
1. Instalar Python
2. Instalar Google Chrome
3. Descargar chromedriver.exe compatible con la versión de Chrome
4. Colocar chromedriver.exe dentro de app/
5. Instalar dependencias:
   py -m pip install -r app/requirements.txt


Ejecución local
cd app
py main.py
Construcción Docker
docker build -t caso2:v1 .
docker build -f Dockerfile.optimizado -t caso2:v2 .
docker build -f Dockerfile.multistage -t caso2:v3 .
Ejecución

docker run --rm caso2:v1
Salida
El Excel se guarda en output/.

URL del repositorio: https://github.com/yashira692/practica01

Nota:
El proyecto utiliza Selenium para automatizar consultas en el portal ONPE.
La ejecución completa se probó en entorno local Windows.
Para ejecución en Docker se requeriría instalar navegador dentro del contenedor.
