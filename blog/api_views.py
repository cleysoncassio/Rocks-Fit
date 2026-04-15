from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from blog.models import Aluno, Schedule, Program
from django.utils import timezone

@api_view(['POST'])
@permission_classes([AllowAny])
def aluno_login(request):
    """
    Login simples do aluno via CPF e Matrícula.
    Em um cenário real, usaríamos autenticação via Token.
    """
    cpf = request.data.get('cpf', '').replace('.', '').replace('-', '')
    matricula = request.data.get('matricula', '')

    if not cpf or not matricula:
        return Response({'success': False, 'message': 'CPF e Matrícula são obrigatórios.'}, status=400)

    aluno = Aluno.objects.filter(cpf__contains=cpf, matricula=matricula).first()

    if not aluno:
        return Response({'success': False, 'message': 'Aluno não encontrado.'}, status=404)

    # Dados do acesso
    status = "bloqueado"
    vencimento = "Nenhum plano ativo"
    if hasattr(aluno, 'acesso'):
        status = aluno.acesso.status_catraca
        if aluno.acesso.data_vencimento:
            vencimento = aluno.acesso.data_vencimento.strftime('%d/%m/%Y')

    return Response({
        'success': True,
        'aluno': {
            'id': aluno.id,
            'nome': aluno.nome_completo,
            'matricula': aluno.matricula,
            'status': status,
            'vencimento': vencimento,
            'foto': request.build_absolute_uri(aluno.foto.url) if aluno.foto else None
        }
    })

@api_view(['GET'])
@permission_classes([AllowAny])
def get_gym_schedule(request):
    """
    Retorna a programação semanal da academia para o app.
    """
    days_data = []
    schedules = Schedule.objects.all().select_related('trainer', 'program')
    
    for d_id, d_name in [
        ('monday', 'Segunda'),
        ('tuesday', 'Terça'),
        ('wednesday', 'Quarta'),
        ('thursday', 'Quinta'),
        ('friday', 'Sexta'),
        ('saturday', 'Sábado'),
        ('sunday', 'Domingo'),
    ]:
        day_classes = []
        for s in schedules:
            if s.day == d_id:
                day_classes.append({
                    'id': s.id,
                    'start_time': s.start_time.strftime('%H:%M'),
                    'end_time': s.end_time.strftime('%H:%M'),
                    'program': s.program.name,
                    'trainer': s.trainer.name,
                    'icon': request.build_absolute_uri(s.program.icon.url) if s.program.icon else None
                })
        
        days_data.append({
            'day': d_name,
            'classes': day_classes
        })

    return Response({
        'success': True,
        'schedule': days_data
    })

@api_view(['GET'])
@permission_classes([AllowAny])
def aluno_profile(request, aluno_id):
    """
    Retorna detalhes completos do perfil de um aluno.
    """
    aluno = Aluno.objects.filter(id=aluno_id).select_related('acesso').first()
    if not aluno:
        return Response({'success': False, 'message': 'Aluno não encontrado.'}, status=404)
    
    acesso = getattr(aluno, 'acesso', None)
    
    return Response({
        'success': True,
        'profile': {
            'nome': aluno.nome_completo,
            'matricula': aluno.matricula,
            'cpf': aluno.cpf,
            'email': aluno.email,
            'whatsapp': aluno.whatsapp,
            'status': acesso.status_catraca if acesso else "pendente",
            'vencimento': acesso.data_vencimento.strftime('%d/%m/%Y') if acesso and acesso.data_vencimento else None,
            'foto': request.build_absolute_uri(aluno.foto.url) if aluno.foto else None
        }
    })
