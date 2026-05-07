#!/bin/bash

# Script de configuração para Biometria Digital Rocks-Fit
echo "🚀 Configurando ambiente para Biometria Digital..."

# 1. Instalar pacotes necessários (se ainda não estiverem)
# O usuário precisará rodar isso com sudo
echo "📦 Instalando fprintd e dependências..."
sudo apt-get update
sudo apt-get install -y fprintd libpam-fprintd

# 2. Configurar permissões para o scanner
# Adiciona o usuário atual ao grupo input se necessário
sudo usermod -a -G input $USER

# 3. Nota sobre usuários
echo ""
echo "ℹ️ IMPORTANTE: O fprintd gerencia digitais por usuário do sistema."
echo "Para cadastrar centenas de alunos, o sistema tentará usar nomes 'student_MATRICULA'."
echo "Se o fprintd exigir que o usuário exista, você pode criá-los em massa ou"
echo "configurar o fprintd para usar um backend customizado."
echo ""
echo "✅ Configuração básica concluída. Reinicie o Módulo de Recepção."
