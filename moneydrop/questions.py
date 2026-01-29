from __future__ import annotations

from .models import Question


def build_question_bank() -> list[Question]:
    """Question bank: Droit d'auteur (grands principes).

    - 4 choices (A/B/C/D), 1 correct answer.
    - Each question includes a short explanation for the host screen after reveal.
    """

    return [
        # --- FACILE ---
        Question(
            category="DROIT D'AUTEUR",
            prompt="En droit d'auteur, qu'est-ce qui declenche la protection d'une oeuvre ?",
            answers={
                "A": "Le depot a l'INPI",
                "B": "La publication sur Internet",
                "C": "L'originalite",
                "D": "Le paiement d'une taxe",
            },
            correct="C",
            explanation="La protection nait automatiquement si l'oeuvre est originale (empreinte de la personnalite de l'auteur). Aucun depot n'est requis. En pratique, on peut juste conserver des preuves de creation (dates, fichiers, mails) en cas de litige.",
        ),
        Question(
            category="DROIT D'AUTEUR",
            prompt="Une idee (ex: 'un roman sur un magicien a l'ecole') est-elle protegee par le droit d'auteur ?",
            answers={
                "A": "Oui, toujours",
                "B": "Non, seule la forme / l'expression est protegee",
                "C": "Oui, si l'idee est nouvelle",
                "D": "Oui, si l'auteur est celebre",
            },
            correct="B",
            explanation="Le droit d'auteur protege la forme originale (texte, images, mise en forme...), pas l'idee en tant que telle. Deux personnes peuvent donc avoir la meme idee, tant qu'elles n'imitent pas la meme expression.",
        ),
        Question(
            category="DROIT D'AUTEUR",
            prompt="Qui est auteur au sens du droit d'auteur ?",
            answers={
                "A": "Uniquement une personne physique",
                "B": "Uniquement une personne morale (societe)",
                "C": "Toujours l'employeur",
                "D": "Toujours le client qui paye",
            },
            correct="A",
            explanation="Par principe, l'auteur est une personne physique: l'humain qui cree. Les droits patrimoniaux peuvent ensuite etre cedes/licencies a une societe, mais la qualite d'auteur reste attachee a la personne.",
        ),
        # --- MOYEN ---
        Question(
            category="DROIT D'AUTEUR",
            prompt="En France, la duree 'classique' de protection patrimoniale est de :",
            answers={
                "A": "25 ans apres la creation",
                "B": "50 ans apres la publication",
                "C": "70 ans apres la mort de l'auteur",
                "D": "Illimitee",
            },
            correct="C",
            explanation="Regle generale: 70 ans apres la mort de l'auteur. Il existe des cas particuliers (oeuvres de collaboration, posthumes, prorogations historiques), mais c'est la base a retenir.",
        ),
        Question(
            category="DROIT D'AUTEUR",
            prompt="Le droit moral (en France) est en principe :",
            answers={
                "A": "Cessible et limite a 10 ans",
                "B": "Perpetuel, inalienable et imprescriptible",
                "C": "Uniquement financier",
                "D": "Reserve aux oeuvres publiees",
            },
            correct="B",
            explanation="Le droit moral protege le lien auteur/oeuvre (paternite, respect de l'oeuvre, divulgation, retrait). Il est en principe perpetuel, inalienable et imprescriptible, meme si les droits patrimoniaux ont ete cedes.",
        ),
        Question(
            category="DROIT D'AUTEUR",
            prompt="Une cession de droits d'auteur est valable si :",
            answers={
                "A": "Elle est toujours orale",
                "B": "Elle est ecrite et precise les droits cedes (etendue/duree/territoire)",
                "C": "Elle couvre automatiquement 'tous supports, tous pays, pour toujours'",
                "D": "Elle est validee par un notaire",
            },
            correct="B",
            explanation="En pratique, on exige un ecrit et une delimitation des droits (reproduction, representation, adaptation...), de la duree et du territoire. Une formule trop vague (\"tout, partout, pour toujours\") est risquee et peut etre contestee.",
        ),
        # --- DIFFICILE ---
        Question(
            category="DROIT D'AUTEUR",
            prompt="La courte citation est licite si :",
            answers={
                "A": "On cite sans mentionner la source",
                "B": "On cite une oeuvre non divulguee",
                "C": "La citation est courte, justifiee par le but et la source est indiquee",
                "D": "On cite au moins 50% de l'oeuvre",
            },
            correct="C",
            explanation="Exception de citation: l'oeuvre doit etre divulguee, la citation doit etre breve et justifiee par le but (critique, analyse, enseignement...). Il faut indiquer la source et le nom de l'auteur, et ne pas remplacer l'oeuvre par la citation.",
        ),
        Question(
            category="DROIT D'AUTEUR",
            prompt="Dans une 'oeuvre collective' (ex: encyclopedie dirigee et publiee par une societe), les droits patrimoniaux appartiennent en principe :",
            answers={
                "A": "A chaque contributeur, uniquement",
                "B": "A la personne (physique ou morale) sous le nom de laquelle l'oeuvre est divulguee",
                "C": "Au premier contributeur",
                "D": "A l'Etat",
            },
            correct="B",
            explanation="Dans l'oeuvre collective, l'initiative, la direction et la publication sont assumees par une personne (souvent une societe). Les droits patrimoniaux appartiennent en principe a celle sous le nom de laquelle l'oeuvre est divulguee, meme s'il y a plusieurs contributeurs.",
        ),
        Question(
            category="DROIT D'AUTEUR",
            prompt="Une oeuvre derivee (ex: traduction, adaptation) necessite en principe :",
            answers={
                "A": "Aucune autorisation si elle est gratuite",
                "B": "L'autorisation de l'auteur de l'oeuvre premiere (sauf exception)",
                "C": "Seulement un depot a l'INPI",
                "D": "Un simple changement de titre",
            },
            correct="B",
            explanation="La traduction/adaptation exploite l'oeuvre premiere: il faut l'accord du titulaire des droits, sauf exception legale. L'auteur de l'adaptation a des droits sur sa contribution, mais pas le droit d'exploiter l'original sans autorisation.",
        ),
        Question(
            category="DROIT D'AUTEUR",
            prompt="L'exception de parodie est en principe possible si :",
            answers={
                "A": "Il y a une intention humoristique et pas de risque de confusion",
                "B": "On reproduit l'oeuvre a l'identique",
                "C": "On ne change rien mais on met 'parodie' en titre",
                "D": "On parodie uniquement des oeuvres dans le domaine public",
            },
            correct="A",
            explanation="La parodie suppose une intention humoristique et l'absence de confusion avec l'oeuvre premiere. Elle doit aussi rester proportionnee (pas d'abus) et ne pas detourner l'oeuvre au-dela de ce qui est necessaire a l'effet parodique.",
        ),
    ]
