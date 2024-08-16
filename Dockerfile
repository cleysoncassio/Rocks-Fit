# Usar a imagem base do Python
FROM python:3.9

# Configurar o diretório de trabalho
WORKDIR /Rocks-Fit

# Copiar os arquivos do projeto
COPY . /app

# Instalar dependências
RUN pip install requirements.txt
RUN pip install requirements-tests.txt

# Comando para iniciar a aplicação
CMD ["pipenv", "run", "gunicorn", "-b", ":$PORT", "mng runserver", "main:app",  ":8080", "myproject.wsgi"]
