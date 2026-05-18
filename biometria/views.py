from rest_framework.decorators import api_view
from rest_framework.response import Response
import base64
import cv2
import numpy as np
from deepface import DeepFace
from django.conf import settings
from blog.models import Aluno
try:
    import redis
    # Conexão Redis para cache de resultados
    redis_url = getattr(settings, "REDIS_URL", "redis://localhost:6379/0")
    redis_client = redis.from_url(redis_url)
except (ImportError, Exception):
    redis_client = None

import logging

logger = logging.getLogger(__name__)

@api_view(["GET", "POST"])
def verificar_biometria(request):
    if request.method == "GET":
        return Response({"status": "ready", "engine": "DeepFace/ArcFace"}, status=200)
    """
    Endpoint para verificação facial. 
    Recebe imagem em base64, extrai embedding e compara no pgvector.
    """
    img_b64 = request.data.get("image")
    if not img_b64:
        return Response({"matricula": "NO_MATCH", "error": "Imagem não fornecida"}, status=400)

    try:
        # Decodifica base64
        img_bytes = base64.b64decode(img_b64)
        np_arr = np.frombuffer(img_bytes, np.uint8)
        frame = cv2.imdecode(np_arr, cv2.IMREAD_COLOR)
        
        if frame is None:
             return Response({"matricula": "NO_MATCH", "error": "Falha ao decodificar imagem"}, status=400)

        # Gera embedding usando ArcFace (DeepFace)
        # enforce_detection=False para evitar erros se o rosto não for detectado perfeitamente no frame
        results = DeepFace.represent(
            img_path=frame,
            model_name="ArcFace",
            enforce_detection=False,
            detector_backend="skip"
        )
        
        if not results:
            return Response({"matricula": "NO_MATCH"})

        # Busca manual otimizada para ArcFace (Cosine Similarity)
        threshold = 0.55 # Threshold otimizado para alta fidelidade (evita falsos positivos)
        aluno_list = Aluno.objects.exclude(facial_embedding__isnull=True).values('matricula', 'nome_completo', 'facial_embedding')
        
        best_match = None
        min_dist = 999.0
        
        embedding = results[0]["embedding"]
        embedding_np = np.array(embedding)
        norm_a = np.linalg.norm(embedding_np)
        
        for a in aluno_list:
            try:
                stored_embedding = np.array(a['facial_embedding'])
                norm_b = np.linalg.norm(stored_embedding)
                
                # Cosine Distance: 1 - (A . B / (|A| * |B|))
                cosine_sim = np.dot(embedding_np, stored_embedding) / (norm_a * norm_b)
                dist = 1 - cosine_sim
                
                if dist < min_dist:
                    min_dist = dist
                    best_match = a
            except Exception as e:
                logger.error(f"⚠️ [BIOMETRIA] Erro ao comparar com {a.get('matricula')}: {e}")
                continue

        if best_match:
            logger.info(f"🔍 [BIOMETRIA] Melhor match: {best_match['nome_completo']} | Distância: {min_dist:.4f} (Threshold: {threshold})")

        if best_match and min_dist < threshold:
            return Response({
                "matricula": best_match['matricula'],
                "nome": best_match['nome_completo'],
                "distancia": float(min_dist)
            })

        return Response({"matricula": "NO_MATCH", "best_dist": float(min_dist) if best_match else 1.0})

    except Exception as e:
        logger.error(f"❌ [BIOMETRIA] Erro na API: {e}")
        return Response({"matricula": "NO_MATCH", "error": str(e)}, status=500)
