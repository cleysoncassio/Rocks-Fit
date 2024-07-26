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
   git clone https://github.com/seu-usuario/rocks-fit-gym-website.git
   cd rocks-fit-gym-website

2. **Crie e Ative um Ambiente Virtual**

    ```bash
    python -m venv venv
    source venv/bin/activate  # No Windows, use `venv\Scripts\activate`


3. **Instale as Dependências**

    ```bash
    pip install -r requirements.txt


4. **Configure o Banco de Dados**

    A configuração padrão usa SQLite, então não é necessário configurar um banco de dados adicional. Para usar outra base de dados, ajuste o settings.py de acordo.

5. **Aplique as Migrações**

    ```bash
    python manage.py makemigrations
    python manage.py migrate

6. **Crie um Superusuário**

    ```bash
    python manage.py createsuperuser

7. **Inicie o Servidor de Desenvolvimento**
    ```bash
    python manage.py runserver

8. **Acesse o Site**

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

Para quaisquer dúvidas ou sugestões, sinta-se à vontade para entrar em contato através do e-mail: cleysoncassio@gmail.com whatsapp: 84 99805-9947

Divirta-se e mantenha-se em forma! 💪