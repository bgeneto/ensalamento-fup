"""
Mock API clients for Sistema de Oferta and Brevo integration.

Provides simulated API responses for development and testing without
requiring actual external service connectivity.
"""

from typing import List, Dict, Any
from dataclasses import dataclass
from datetime import datetime, timedelta
import random
import json


@dataclass
class SistemaOfertaDemanda:
    """Mock demand data from Sistema de Oferta."""

    codigo_disciplina: str
    nome_disciplina: str
    professores: List[str]
    turma: str
    vagas: int
    horario_bruto: str  # e.g., "24M12 6T34"
    nivel: str


class MockSistemaOfertaAPI:
    """
    Mock client for Sistema de Oferta API.

    Returns simulated course demand data for a given semester.
    """

    # Mock course database
    MOCK_COURSES = [
        {
            "codigo": "CIC0001",
            "nome": "Introdução à Computação",
            "professores": ["Prof. Ana Silva", "Prof. Bruno Costa"],
            "vagas": 40,
            "horario": "24M12",  # Seg e Ter, blocos M1 e M2
            "nivel": "Graduação",
        },
        {
            "codigo": "CIC0002",
            "nome": "Programação I",
            "professores": ["Prof. Carlos Oliveira"],
            "vagas": 35,
            "horario": "35M123",  # Ter e Qua, blocos M1, M2, M3
            "nivel": "Graduação",
        },
        {
            "codigo": "CIC0101",
            "nome": "Estrutura de Dados",
            "professores": ["Prof. Daniela Ferreira", "Prof. Eduardo Santos"],
            "vagas": 30,
            "horario": "24T12",  # Seg e Ter, blocos T1 e T2
            "nivel": "Graduação",
        },
        {
            "codigo": "CIC0201",
            "nome": "Algoritmos",
            "professores": ["Prof. Fernanda Lima"],
            "vagas": 25,
            "horario": "35T34",  # Ter e Qua, blocos T3 e T4
            "nivel": "Graduação",
        },
        {
            "codigo": "CIC0301",
            "nome": "Banco de Dados",
            "professores": ["Prof. Gabriel Martins"],
            "vagas": 28,
            "horario": "45M12",  # Qua e Qui, blocos M1 e M2
            "nivel": "Graduação",
        },
        {
            "codigo": "CIC0401",
            "nome": "Sistemas Operacionais",
            "professores": ["Prof. Helena Rocha"],
            "vagas": 32,
            "horario": "56T123",  # Qui e Sex, blocos T1, T2, T3
            "nivel": "Graduação",
        },
        {
            "codigo": "CIC5001",
            "nome": "Tópicos Avançados em Computação",
            "professores": ["Prof. Igor Costa"],
            "vagas": 15,
            "horario": "24M34",  # Seg e Ter, blocos M3 e M4
            "nivel": "Pós-Graduação",
        },
        {
            "codigo": "CIC5002",
            "nome": "Machine Learning",
            "professores": ["Prof. Iris Dias"],
            "vagas": 20,
            "horario": "35N12",  # Ter e Qua, blocos N1 e N2
            "nivel": "Pós-Graduação",
        },
    ]

    @staticmethod
    def get_demands(semestre: str) -> List[Dict[str, Any]]:
        """
        Get mock course demand data for a semester.

        Args:
            semestre: Semester identifier (e.g., "2025.1")

        Returns:
            List of course demand dictionaries
        """
        demands = []
        for i, course in enumerate(MockSistemaOfertaAPI.MOCK_COURSES):
            demand = {
                "id": i + 1,
                "semestre": semestre,
                "codigo_disciplina": course["codigo"],
                "nome_disciplina": course["nome"],
                "professores_disciplina": ", ".join(course["professores"]),
                "turma_disciplina": f"TUR{i+1:02d}",
                "vagas_disciplina": course["vagas"],
                "horario_sigaa_bruto": course["horario"],
                "nivel_disciplina": course["nivel"],
                "timestamp": datetime.now().isoformat(),
            }
            demands.append(demand)

        return demands

    @staticmethod
    def get_demand(semestre: str, codigo_disciplina: str) -> Dict[str, Any]:
        """
        Get mock demand for a specific course.

        Args:
            semestre: Semester identifier
            codigo_disciplina: Course code

        Returns:
            Course demand dictionary
        """
        for course in MockSistemaOfertaAPI.MOCK_COURSES:
            if course["codigo"] == codigo_disciplina:
                return {
                    "semestre": semestre,
                    "codigo_disciplina": course["codigo"],
                    "nome_disciplina": course["nome"],
                    "professores_disciplina": ", ".join(course["professores"]),
                    "vagas_disciplina": course["vagas"],
                    "horario_sigaa_bruto": course["horario"],
                    "nivel_disciplina": course["nivel"],
                    "timestamp": datetime.now().isoformat(),
                }

        return None


class MockBrevoAPI:
    """
    Mock client for Brevo (Sendinblue) email API.

    Simulates email sending without actually sending emails.
    """

    MOCK_CONTACTS = [
        {
            "email": "professor1@fup.unb.br",
            "first_name": "Ana",
            "last_name": "Silva",
        },
        {
            "email": "professor2@fup.unb.br",
            "first_name": "Bruno",
            "last_name": "Costa",
        },
        {
            "email": "professor3@fup.unb.br",
            "first_name": "Carlos",
            "last_name": "Oliveira",
        },
        {
            "email": "professor4@fup.unb.br",
            "first_name": "Daniela",
            "last_name": "Ferreira",
        },
    ]

    @staticmethod
    def send_email(
        to: str,
        subject: str,
        template_id: int = None,
        params: Dict[str, str] = None,
        html_content: str = None,
    ) -> Dict[str, Any]:
        """
        Mock email sending via Brevo.

        Args:
            to: Recipient email address
            subject: Email subject
            template_id: Optional Brevo template ID
            params: Template parameters
            html_content: Direct HTML content

        Returns:
            Mock response with message ID
        """
        message_id = random.randint(100000, 999999)

        return {
            "messageId": f"mock_msg_{message_id}",
            "status": "success",
            "recipient": to,
            "subject": subject,
            "template_id": template_id,
            "sent_at": datetime.now().isoformat(),
        }

    @staticmethod
    def get_contact(email: str) -> Dict[str, Any]:
        """
        Get mock contact information from Brevo.

        Args:
            email: Email address to look up

        Returns:
            Contact dictionary or None
        """
        for contact in MockBrevoAPI.MOCK_CONTACTS:
            if contact["email"] == email:
                return {
                    "email": contact["email"],
                    "first_name": contact["first_name"],
                    "last_name": contact["last_name"],
                    "attributes": {
                        "LAST_UPDATED": datetime.now().isoformat(),
                        "STATUS": "active",
                    },
                }
        return None

    @staticmethod
    def create_contact(
        email: str, first_name: str = "", last_name: str = ""
    ) -> Dict[str, Any]:
        """
        Mock create contact in Brevo.

        Args:
            email: Email address
            first_name: First name
            last_name: Last name

        Returns:
            Mock response with contact ID
        """
        contact_id = random.randint(1000, 9999)

        return {
            "id": contact_id,
            "email": email,
            "first_name": first_name,
            "last_name": last_name,
            "created_at": datetime.now().isoformat(),
            "status": "success",
        }

    @staticmethod
    def send_allocation_email(
        recipient_email: str,
        professor_name: str,
        discipline_name: str,
        room_name: str,
        schedule: str,
    ) -> Dict[str, Any]:
        """
        Mock send allocation notification email to professor.

        Args:
            recipient_email: Professor's email
            professor_name: Professor's name
            discipline_name: Course name
            room_name: Allocated room
            schedule: Schedule information

        Returns:
            Mock email send response
        """
        subject = f"Alocação de Sala: {discipline_name}"

        html_content = f"""
        <h2>Alocação de Sala Confirmada</h2>
        <p>Olá {professor_name},</p>
        <p>Sua disciplina <strong>{discipline_name}</strong> foi alocada para a sala <strong>{room_name}</strong>.</p>
        <p><strong>Horário:</strong> {schedule}</p>
        <p>Qualquer dúvida, entre em contato com a secretaria.</p>
        """

        return MockBrevoAPI.send_email(
            to=recipient_email,
            subject=subject,
            html_content=html_content,
        )


class APIIntegrationFactory:
    """
    Factory for API clients.

    In production, this would instantiate real API clients.
    For now, it returns mock clients.
    """

    @staticmethod
    def get_sistema_oferta_client():
        """Get Sistema de Oferta API client."""
        return MockSistemaOfertaAPI()

    @staticmethod
    def get_brevo_client():
        """Get Brevo API client."""
        return MockBrevoAPI()


# Convenience aliases
sistema_oferta_api = APIIntegrationFactory.get_sistema_oferta_client()
brevo_api = APIIntegrationFactory.get_brevo_client()
