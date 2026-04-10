import os
import django

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "sitio.settings")
django.setup()

from blog.models import Program, Trainer, ContactInfo, Schedule
from django.utils import timezone
from datetime import time

def populate():
    # Create Contact Info
    if not ContactInfo.objects.exists():
        ContactInfo.objects.create(
            address="Rua Cel. Flaminio, 32 - Santos Reis, Natal-RN",
            phone="+55 84 99947-0586",
            email="academiarocksfit@gmail.com",
            website="http://www.rocksfit.com"
        )
        print("Created ContactInfo")

    # Create Programs
    programs = [
        {"name": "Musculação", "description": "Fortalecimento muscular e hipertrofia."},
        {"name": "Funcional", "description": "Melhora do condicionamento físico geral."},
        {"name": "Cardio Dance", "description": "Aulas de dança para queimar calorias."},
    ]
    
    created_programs = []
    for p_data in programs:
        program, created = Program.objects.get_or_create(name=p_data["name"], defaults=p_data)
        created_programs.append(program)
        if created:
            print(f"Created Program: {program.name}")

    # Create Trainers
    trainers = [
        {"name": "Carlos Silva", "title": "Personal Trainer", "description": "Especialista em musculação."},
        {"name": "Ana Souza", "title": "Instrutora de Dança", "description": "Especialista em ritmos latinos."},
        {"name": "Pedro Oliveira", "title": "Coach Funcional", "description": "Foco em alta performance."},
    ]

    created_trainers = []
    for t_data in trainers:
        trainer, created = Trainer.objects.get_or_create(name=t_data["name"], defaults=t_data)
        created_trainers.append(trainer)
        if created:
            print(f"Created Trainer: {trainer.name}")

    # Create Schedules (Sample)
    if created_programs and created_trainers:
        schedules = [
            {"day": "monday", "start_time": time(8, 0), "end_time": time(9, 0), "program": created_programs[0], "trainer": created_trainers[0]},
            {"day": "wednesday", "start_time": time(18, 0), "end_time": time(19, 0), "program": created_programs[1], "trainer": created_trainers[2]},
            {"day": "friday", "start_time": time(19, 0), "end_time": time(20, 0), "program": created_programs[2], "trainer": created_trainers[1]},
        ]
        
        for s_data in schedules:
            schedule, created = Schedule.objects.get_or_create(
                day=s_data["day"], 
                start_time=s_data["start_time"], 
                program=s_data["program"],
                defaults={"trainer": s_data["trainer"], "end_time": s_data["end_time"]}
            )
            if created:
                print(f"Created Schedule: {schedule}")

    print("Population complete!")

if __name__ == "__main__":
    populate()
