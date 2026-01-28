from __future__ import annotations

from .models import Question


def build_question_bank() -> list[Question]:
    """Banque de questions.

    Exigences :
    - 2 types : MUSIQUE et DROIT/INFORMATIQUE
    - Les questions droit/info sont STRICTEMENT dans les thèmes fournis.
    - Au moins une question exploite le tableau récapitulatif.
    """

    q: list[Question] = [
        # --- NIVEAU FACILE ---
        Question(
            category="DROIT/INFO",
            prompt="En France, le CODE SOURCE d'un logiciel est protégé par :",
            answers={
                "A": "Le Brevet industriel",
                "B": "Le Droit d'Auteur",
                "C": "Le Secret Défense",
                "D": "Le Droit des Marques",
            },
            correct="B",
        ),
        Question(
            category="DROIT/INFO",
            prompt="Que signifie l'acronyme RGPD ?",
            answers={
                "A": "Règlement Global pour la Protection des Données",
                "B": "Régime Général de la Propriété des Données",
                "C": "Règlement Général sur la Protection des Données",
                "D": "Registre Gouvernemental des Preuves Digitales",
            },
            correct="C",
        ),
        Question(
            category="DROIT/INFO",
            prompt="Le principe de 'Minimisation' (RGPD) impose de :",
            answers={
                "A": "Collecter le moins de données possible",
                "B": "Minimiser le coût du stockage",
                "C": "Réduire la taille de la base de données",
                "D": "Ne garder les données que 24h",
            },
            correct="A",
        ),

        # --- NIVEAU MOYEN ---
        Question(
            category="DROIT/INFO",
            prompt="Pour protéger la STRUCTURE d'une base de données par le droit d'auteur, elle doit être :",
            answers={
                "A": "Volumineuse",
                "B": "Originale",
                "C": "Rentable",
                "D": "Secrète",
            },
            correct="B",
        ),
        Question(
            category="DROIT/INFO",
            prompt="Quel droit protège l'INVESTISSEMENT financier (le contenu) d'une base de données ?",
            answers={
                "A": "Le Droit Sui Generis",
                "B": "Le Droit à l'image",
                "C": "Le Copyright",
                "D": "Le Droit moral",
            },
            correct="A",
        ),
        Question(
            category="DROIT/INFO",
            prompt="Une adresse IP ou un identifiant publicitaire sont-ils des Données Personnelles (DCP) ?",
            answers={
                "A": "Non, jamais",
                "B": "Oui, car ils permettent d'identifier indirectement",
                "C": "Seulement pour les personnes célèbres",
                "D": "Non, ce sont des données machines",
            },
            correct="B",
        ),

        # --- NIVEAU DIFFICILE ---
        Question(
            category="DROIT/INFO",
            prompt="J'ai le droit de créer un logiciel qui a exactement les mêmes fonctionnalités que Excel si :",
            answers={
                "A": "Je ne copie pas le code source",
                "B": "Je le distribue gratuitement",
                "C": "Je change le nom du logiciel",
                "D": "C'est strictement interdit",
            },
            correct="A",
        ),
        Question(
            category="DROIT/INFO",
            prompt="Quelle est la durée de protection du droit Sui Generis (producteur BDD) ?",
            answers={
                "A": "70 ans après la mort de l'auteur",
                "B": "10 ans renouvelables",
                "C": "15 ans à compter de l'achèvement",
                "D": "Illimitée tant que la base existe",
            },
            correct="C",
        ),
        Question(
            category="DROIT/INFO",
            prompt="Stocker des mots de passe 'en clair' (non chiffrés) est une violation de l'obligation de :",
            answers={
                "A": "Finalité",
                "B": "Transparence",
                "C": "Sécurité",
                "D": "Portabilité",
            },
            correct="C",
        ),

        # --- LA QUESTION QUI TUE (FINALE) ---
        Question(
            category="DROIT/INFO",
            prompt="Quelle est la sanction administrative MAXIMALE possible par la CNIL ?",
            answers={
                "A": "300 000 €",
                "B": "3 Millions €",
                "C": "10 Millions € ou 2% du CA",
                "D": "20 Millions € ou 4% du CA",
            },
            correct="D",
        )
    ]

    return q