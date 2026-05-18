#!/bin/bash
# Script para autorizar o fprintd e desativar economia de energia USB no leitor biométrico
RULE_FILE="/etc/polkit-1/rules.d/50-fprintd.rules"
UDEV_FILE="/etc/udev/rules.d/99-disable-fingerprint-autosuspend.rules"

echo "--------------------------------------------------------"
echo "🛡️ ROCKS-FIT: CONFIGURADOR BIOMÉTRICO INDUSTRIAL"
echo "--------------------------------------------------------"

# 1. Cria regra Polkit para evitar solicitações de senha pelo fprintd
cat <<EOF > /tmp/50-fprintd.rules
polkit.addRule(function(action, subject) {
    if (action.id == "net.reactivated.fprint.device.enroll" ||
        action.id == "net.reactivated.fprint.device.verify" ||
        action.id == "net.reactivated.fprint.device.set-config") {
        return polkit.Result.YES;
    }
});
EOF

echo "🔑 Configurando permissões do Polkit..."
sudo mv /tmp/50-fprintd.rules $RULE_FILE
sudo chown root:root $RULE_FILE
sudo chmod 644 $RULE_FILE

# 2. Cria regra Udev para desativar o Autosuspend do sensor DigitalPersona (Evita verify-unknown-error)
echo "⚡ Desativando economia de energia (autosuspend) para o Leitor DigitalPersona (05ba:000a)..."
cat <<EOF > /tmp/99-disable-fingerprint-autosuspend.rules
# Desativa economia de energia USB para o leitor DigitalPersona
ACTION=="add", SUBSYSTEM=="usb", ATTR{idVendor}=="05ba", ATTR{idProduct}=="000a", TEST=="power/control", ATTR{power/control}="on"
EOF

sudo mv /tmp/99-disable-fingerprint-autosuspend.rules $UDEV_FILE
sudo chown root:root $UDEV_FILE
sudo chmod 644 $UDEV_FILE

# 3. Recarrega as regras e reinicia serviços
echo "🔄 Recarregando subsistema de hardware UDEV..."
sudo udevadm control --reload-rules
sudo udevadm trigger

echo "🔄 Reiniciando o daemon de biometria fprintd..."
sudo systemctl restart fprintd.service 2>/dev/null || true

echo "--------------------------------------------------------"
echo "✅ CONFIGURAÇÃO CONCLUÍDA COM SUCESSO!"
echo "• O sensor biométrico agora está liberado para o sistema."
echo "• O autosuspend foi desativado para evitar travamentos/tela preta."
echo "👉 DICA: Por favor, desconecte e reconecte o leitor USB agora!"
echo "--------------------------------------------------------"
