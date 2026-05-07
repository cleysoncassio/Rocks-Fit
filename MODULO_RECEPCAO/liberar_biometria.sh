#!/bash/bin
# Script para autorizar o fprintd a cadastrar biometria sem pedir senha do root
RULE_FILE="/etc/polkit-1/rules.d/50-fprintd.rules"

echo "--------------------------------------------------------"
echo "ROCKS-FIT: CONFIGURADOR DE PERMISSÕES BIOMÉTRICAS"
echo "--------------------------------------------------------"

cat <<EOF > /tmp/50-fprintd.rules
polkit.addRule(function(action, subject) {
    if (action.id == "net.reactivated.fprint.device.enroll" ||
        action.id == "net.reactivated.fprint.device.verify" ||
        action.id == "net.reactivated.fprint.device.set-config") {
        return polkit.Result.YES;
    }
});
EOF

echo "Solicitando permissão root para mover o arquivo de regra..."
sudo mv /tmp/50-fprintd.rules $RULE_FILE
sudo chown root:root $RULE_FILE
sudo chmod 644 $RULE_FILE

echo "--------------------------------------------------------"
echo "✅ SUCESSO! O sensor biométrico agora está liberado."
echo "Reinicie o sistema ou o serviço polkit se necessário."
echo "--------------------------------------------------------"
