import re

with open('MODULO_RECEPCAO/ponte_rocksfit_flet.py', 'r') as f:
    content = f.read()

# Encontra a função route_change e substitui tudo até '        page.update()'
new_func = """    def route_change(route):
        page.views.clear()
        if "/monitor" in page.route:
            surf = "#0e0e0e"
            surf_low = "#131313"
            surf_high = "#201f1f"
            surf_highest = "#262626"
            primary = "#ff7a2f"
            
            titulo = ft.Row([
                ft.Text("BIOMETRIA ", size=56, font_family="Space Grotesk", weight="bold", italic=True, color="#ffffff"),
                ft.Text("ATIVA", size=56, font_family="Space Grotesk", weight="bold", italic=True, color=primary)
            ], spacing=0)
            subtitulo = ft.Text("APROXIME-SE PARA VALIDAR", size=18, color="#adaaaa", weight="w500")
            
            img_cam = ft.Image(src_base64="", fit=ft.ImageFit.COVER, expand=True, border_radius=16)
            
            cam_overlay = ft.Container(
                content=ft.Container(
                    bgcolor="#ff7a2f22",
                    border=ft.border.all(2, "#ff7a2f44"),
                    border_radius=12,
                    width=250, height=250,
                    alignment=ft.Alignment(0,0),
                    content=ft.Icon("face", color=primary, size=48, opacity=0.8)
                ),
                alignment=ft.Alignment(0,0)
            )
            
            lbl_cam_status = ft.Text("AGUARDANDO...", size=14, weight="bold", color="#000000")
            badge_cam_status = ft.Container(
                content=ft.Row([
                    ft.Container(width=12, height=12, border_radius=6, bgcolor="#000000"),
                    lbl_cam_status
                ], alignment="center", spacing=8),
                bgcolor=primary,
                border_radius=20,
                padding=ft.padding.symmetric(horizontal=24, vertical=10),
                margin=ft.padding.only(bottom=30)
            )
            
            cam_container = ft.Container(
                content=ft.Stack([
                    img_cam,
                    cam_overlay,
                    ft.Container(content=badge_cam_status, alignment=ft.alignment.bottom_center)
                ]),
                expand=True,
                bgcolor=surf_highest,
                border_radius=16,
                margin=ft.padding.only(top=20),
                border=ft.border.all(1, "#ffffff10")
            )
            
            left_col = ft.Column([titulo, subtitulo, cam_container], expand=True)
            
            lbl_nome = ft.Text("ACESSO RESTRITO", size=24, font_family="Space Grotesk", weight="bold", color="#ffffff", text_align="center")
            lbl_msg = ft.Text("Posicione-se em frente à câmera para identificação automática", size=14, color="#adaaaa", text_align="center")
            img_perfil = ft.Image(src="https://via.placeholder.com/150", width=120, height=120, border_radius=60, fit=ft.ImageFit.COVER, opacity=0.3)
            
            lbl_status_tag = ft.Text("INATIVO", size=12, weight="bold", color="#ff7351")
            status_container = ft.Container(
                content=lbl_status_tag,
                bgcolor="#ff735133",
                padding=ft.padding.symmetric(horizontal=12, vertical=4),
                border_radius=12
            )
            
            card_perfil = ft.Container(
                content=ft.Column([
                    ft.Container(content=img_perfil, alignment=ft.Alignment(0,0), margin=ft.padding.only(bottom=20)),
                    ft.Container(content=lbl_nome, alignment=ft.Alignment(0,0)),
                    ft.Container(content=lbl_msg, alignment=ft.Alignment(0,0), margin=ft.padding.only(bottom=30)),
                    ft.Row([
                        ft.Text("STATUS", size=12, color="#adaaaa"),
                        status_container
                    ], alignment="spaceBetween"),
                    ft.Divider(color=surf_highest, height=30),
                    ft.Row([
                        ft.Text("UNIDADE", size=12, color="#adaaaa"),
                        ft.Text("ROCKS FIT #01", size=14, weight="bold", color="#ffffff")
                    ], alignment="spaceBetween"),
                ]),
                bgcolor=surf_high,
                padding=30,
                border_radius=20,
            )
            
            card_capacidade = ft.Container(
                content=ft.Column([
                    ft.Row([
                        ft.Text("CAPACIDADE", size=18, font_family="Space Grotesk", weight="bold", italic=True, color="#000000"),
                        ft.Icon("people", color="#000000")
                    ], alignment="spaceBetween"),
                    ft.Row([
                        ft.Text("74%", size=48, font_family="Space Grotesk", weight="bold", color="#000000"),
                        ft.Text("LOTADO", size=12, weight="bold", color="#000000")
                    ], alignment="spaceBetween", vertical_alignment="end"),
                    ft.ProgressBar(value=0.74, color="#000000", bgcolor="#ffffff40", height=8)
                ]),
                gradient=ft.LinearGradient(
                    begin=ft.Alignment(-1, -1),
                    end=ft.Alignment(1, 1),
                    colors=["#ff9159", "#ff7a2f"]
                ),
                padding=30,
                border_radius=20,
                margin=ft.padding.only(top=20)
            )
            
            right_col = ft.Container(
                content=ft.Column([card_perfil, card_capacidade]),
                width=360,
                margin=ft.padding.only(left=40)
            )
            
            monitor_layout = ft.Container(
                content=ft.Column([
                    ft.Row([
                        ft.Text("ROCKS FIT", size=24, font_family="Space Grotesk", weight="bold", italic=True, color=primary),
                        ft.Row([
                            ft.Text("Biometria", color=primary, weight="bold"),
                            ft.Text("Dashboard", color="#adaaaa"),
                            ft.Text("Membros", color="#adaaaa")
                        ], spacing=30),
                        ft.Row([ft.Icon("sensors", color=primary), ft.Icon("notifications", color=primary)], spacing=15)
                    ], alignment="spaceBetween", margin=ft.padding.only(bottom=40)),
                    ft.Row([left_col, right_col], expand=True),
                    ft.Row([
                        ft.Row([
                            ft.Container(width=8, height=8, border_radius=4, bgcolor=primary),
                            ft.Text("SERVER: ONLINE", size=10, weight="bold", color="#adaaaa"),
                            ft.Container(width=8, height=8, border_radius=4, bgcolor=primary, margin=ft.padding.only(left=20)),
                            ft.Text("SCANNER: ACTIVE", size=10, weight="bold", color="#adaaaa"),
                        ]),
                        ft.Text("SÃO PAULO, BR", size=10, color="#adaaaa")
                    ], alignment="spaceBetween", margin=ft.padding.only(top=20))
                ], expand=True),
                expand=True,
                padding=50,
                bgcolor=surf
            )
            
            camera_estado = {"rodando": True}
            
            def loop_camera():
                try:
                    cap = cv2.VideoCapture(0)
                    face_cascade = cv2.CascadeClassifier(cv2.data.haarcascades + 'haarcascade_frontalface_default.xml')
                    cooldown = 0
                    
                    while camera_estado["rodando"] and cap.isOpened():
                        ret, frame = cap.read()
                        if ret:
                            frame = cv2.flip(frame, 1)
                            gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
                            faces = face_cascade.detectMultiScale(gray, 1.1, 5)
                            
                            for (x,y,w,h) in faces:
                                cv2.rectangle(frame, (x,y), (x+w, y+h), (242, 113, 33), 2)
                                
                            if len(faces) > 0 and cooldown <= 0:
                                (x,y,w,h) = faces[0]
                                margin = int(w * 0.2)
                                x1, y1 = max(0, x - margin), max(0, y - margin)
                                x2, y2 = min(frame.shape[1], x + w + margin), min(frame.shape[0], y + h + margin)
                                face_roi = frame[y1:y2, x1:x2]
                                
                                frame_small = cv2.resize(face_roi, (200, 200))
                                gray_webcam = cv2.cvtColor(frame_small, cv2.COLOR_BGR2GRAY)
                                clahe = cv2.createCLAHE(clipLimit=2.0, tileGridSize=(8,8))
                                gray_webcam = clahe.apply(gray_webcam)
                                orb = cv2.ORB_create(700)
                                _, des_webcam = orb.detectAndCompute(gray_webcam, None)
                                
                                if des_webcam is not None:
                                    melhor_aluno = None
                                    melhor_score = 0
                                    bf = cv2.BFMatcher(cv2.NORM_HAMMING, crossCheck=False)
                                    
                                    for mat, perfil in state.get("alunos_perfis", {}).items():
                                        if perfil['des'] is None: continue
                                        try:
                                            matches = bf.knnMatch(des_webcam, perfil['des'], k=2)
                                            bons = [m for m, n in matches if m.distance < 0.8 * n.distance]
                                            score = len(bons)
                                            if score > melhor_score:
                                                melhor_score = score
                                                melhor_aluno = perfil['data']
                                        except: continue
                                        
                                    if melhor_aluno and melhor_score > 35:
                                        print(f"✅ Reconhecido: {melhor_aluno['nome']} (Score: {melhor_score})")
                                        try:
                                            r = requests.get(f"{SITE_URL}/api/catraca-check/{melhor_aluno['matricula']}/?token={SYNC_TOKEN}", timeout=3)
                                            data = r.json() if r.status_code == 200 else melhor_aluno
                                            msg = data.get('mensagem', 'ACESSO LIBERADO').upper()
                                            
                                            lbl_nome.value = data.get('nome', melhor_aluno['nome']).upper()
                                            
                                            furl = melhor_aluno.get("foto_url")
                                            if furl:
                                                if furl.startswith('/'): furl = f"{SITE_URL}{furl}"
                                                img_perfil.src = furl
                                            img_perfil.opacity = 1.0
                                            
                                            if data.get('status') in ['ativo', 'liberado']:
                                                lbl_status_tag.value = "LIBERADO"
                                                lbl_status_tag.color = "#000000"
                                                status_container.bgcolor = "#ffc562"
                                                lbl_cam_status.value = "ACESSO PERMITIDO"
                                                badge_cam_status.bgcolor = "#ffc562"
                                                
                                                import socket
                                                for pta in [1001, 3000, 5000]:
                                                    try:
                                                        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
                                                            sock.settimeout(1)
                                                            sock.connect(("192.168.1.100", pta))
                                                            sock.sendall(b"lgu\\x00Liberou Entrada")
                                                            break
                                                    except: pass
                                            else:
                                                lbl_status_tag.value = "BLOQUEADO"
                                                lbl_status_tag.color = "#000000"
                                                status_container.bgcolor = "#ff7351"
                                                lbl_cam_status.value = "ACESSO NEGADO"
                                                badge_cam_status.bgcolor = "#ff7351"
                                                
                                            lbl_msg.value = msg
                                            lbl_msg.color = "#ffffff"
                                            
                                            cooldown = 100
                                            
                                            def reset():
                                                time.sleep(3)
                                                lbl_nome.value = "ACESSO RESTRITO"
                                                lbl_msg.value = "Posicione-se em frente à câmera para identificação automática"
                                                lbl_msg.color = "#adaaaa"
                                                lbl_status_tag.value = "INATIVO"
                                                lbl_status_tag.color = "#ff7351"
                                                status_container.bgcolor = "#ff735133"
                                                img_perfil.src = "https://via.placeholder.com/150"
                                                img_perfil.opacity = 0.3
                                                lbl_cam_status.value = "AGUARDANDO..."
                                                badge_cam_status.bgcolor = primary
                                                try: page.update()
                                                except: pass
                                            threading.Thread(target=reset, daemon=True).start()
                                            
                                        except Exception as e:
                                            print("Erro na API de liberação:", e)
                                            
                            if cooldown > 0: cooldown -= 1
                                
                            _, buffer = cv2.imencode('.jpg', frame)
                            img_cam.src_base64 = base64.b64encode(buffer).decode('utf-8')
                            try:
                                page.update()
                            except:
                                pass
                        time.sleep(0.03)
                    cap.release()
                except Exception as e:
                    print("Erro na câmera Flet:", e)

            threading.Thread(target=loop_camera, daemon=True).start()

            page.views.append(
                ft.View(
                    "/monitor",
                    [monitor_layout],
                    bgcolor=surf,
                    padding=0
                )
            )
        else:
            # --- VIEW PRINCIPAL (RECEPÇÃO) ---
            page.views.append(
                ft.View(
                    "/",
                    [layout],
                    padding=0,
                    bgcolor=COR_BG
                )
            )
        page.update()"""

pattern = re.compile(r'    def route_change\(route\):.*?        page\.update\(\)', re.DOTALL)
new_content = pattern.sub(new_func, content)

with open('MODULO_RECEPCAO/ponte_rocksfit_flet.py', 'w') as f:
    f.write(new_content)

print("Update completed.")
