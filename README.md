# 🏋️ Rocks Fit Gym Website 🏋️

## 📜 Descrição
Bem-vindo ao projeto do site da academia Rocks Fit! Este repositório contém o código-fonte do site da academia Rocks Fit, situada à Rua Cel. Flaminio, 32, Santos Reis, fundada em 28 de fevereiro de 2014. Este site foi desenvolvido para proporcionar uma experiência online interativa e informativa para os membros da academia.

## 📥 Instalação

### Pré-requisitos

- Python 3.11 ou superior
- Django 5.0.7 ou superior
- Git (para clonar o repositório)

### Passos para Instalação

1. **Clone o Repositório**

   ```bash
   git clone https://github.com/cleysoncassio/Rocks-Fit
   cd Rocks-Fit #aqui você vai entrar na pasta do projeto e executar os comandos abaixo

2. **Dentro da pasta do projeto instale o pipenv**

    ```bash
    pipenv install

4. **Quer contribuir? Instale as Dependências**

    ```bash
    pipenv sync -d # instala as Dependênciasdo projeto

3. **Para conferir a qualidade do código,rode no console**

    ```bash
    flake8 #garante conformidade com as diretrizes de estilo, identifica erros e melhorar a legibilidade e a manutenibilidade do seu código.
    isort . #Ordena e formata automaticamente as declarações de importação em arquivos Python.
    black . #Aplica um estilo de código consistente em todo o projeto Python. PEP8
    safety check #Este comando verifica todas as dependências instaladas no ambiente Python atual.
    coverage #coverage run -m unittest discover #coverage html
    pytest #pipenv run pytest --cov=sitio



5. **Configure o Banco de Dados**

    A configuração padrão usa SQLite, então não é necessário configurar um banco de dados adicional. Para usar outra base de dados, ajuste o settings.py de acordo.

6. **Aplique as Migrações**

    ```bash
    python manage.py makemigrations
    python manage.py migrate

7. **Crie um Superusuário**

    ```bash
    python manage.py createsuperuser #aqui você cria seu usuário do administrador do usuário

8. **Inicie o Servidor de Desenvolvimento**
    ```bash
    python manage.py runserver # Roda o servidor de desenvolvimento

9. **Acesse o Site**

Abra o navegador e vá para http://localhost:8000 para ver o site da academia Rocks Fit em ação.

## 📂 Estrutura do Projeto

```Plaitext
rocks-fit-gym-website/
├── blog/
│   ├── static/
│   │   ├── css/
│   │   ├── images/
│   │   └── js/
│   ├── templates/
│   │   ├── home.html
│   │   ├── programs.html
│   │   ├── schedule.html
│   │   ├── contact.html
│   │   ├── trainers.html
│   │   └── about.html
│   ├── views.py
│   ├── models.py
│   └── urls.py
├── my_django_project/
│   ├── settings.py
│   ├── urls.py
│   └── wsgi.py
├── manage.py
└── README.md
```

##  📜 Licença
Este projeto está licenciado sob a MIT License.

## ✉️ Contato

Para quaisquer dúvidas ou sugestões, sinta-se à vontade para entrar em contato através do e-mail: cleysoncassio@gmail.com whatsapp: + 55 84 99947-0586

Divirta-se e mantenha-se em forma! 💪

[![Build Status](https://app.travis-ci.com/cleysoncassio/Rocks-Fit.svg?token=s5zDkRsrk6xP3ss4bFRp&branch=master)](https://app.travis-ci.com/cleysoncassio/Rocks-Fit)
[![Coverage Status](https://coveralls.io/repos/github/cleysoncassio/Rocks-Fit/badge.svg)](https://coveralls.io/github/cleysoncassio/Rocks-Fit)
[![Updates](https://pyup.io/repos/github/pyupio/pyup/shield.svg)](https://pyup.io/repos/github/pyupio/pyup/)
[![Python 3](https://pyup.io/repos/github/pyupio/pyup/python-3-shield.svg)](https://pyup.io/repos/github/pyupio/pyup/)


Publicado app no heroku: https://sitiodjango-1072730bb6ee.herokuapp.com/