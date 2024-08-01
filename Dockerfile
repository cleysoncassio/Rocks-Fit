# Usar a imagem base do Python
FROM python:3.9

# Configurar o diretório de trabalho
WORKDIR /Rocks-Fit

# Copiar os arquivos do projeto
COPY . /app

# Instalar pipenv e dependências
RUN pip install pipenv
RUN pipenv sync -d

# Comando para iniciar a aplicação
CMD ["pipenv", "run", "gunicorn", "-b", ":$PORT", "mng runserver", "main:app"]
