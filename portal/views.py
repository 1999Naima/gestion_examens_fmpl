# portal/views.py
import json
from datetime import date
from django.shortcuts import render, redirect
from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.decorators import login_required
from django.views.decorators.http import require_http_methods
from django.http import JsonResponse


# ─────────────────────────────────────────────────────────────────
# SURVEILLANT LOGIN
# ─────────────────────────────────────────────────────────────────
@require_http_methods(["GET", "POST"])
def surveillant_login(request):
    if request.user.is_authenticated and _role(request.user) == "surveillant":
        return redirect("portal:surveillant_dashboard")

    if request.method == "POST":
        username = request.POST.get("username", "").strip()
        password = request.POST.get("password", "")
        user = authenticate(request, username=username, password=password)

        if user and user.is_active and _role(user) == "surveillant":
            login(request, user)
            return redirect(request.GET.get("next") or "portal:surveillant_dashboard")

        return render(request, "portal/surveillant_login.html", {
            "error":    "Identifiant ou mot de passe incorrect.",
            "username": username,
        })

    return render(request, "portal/surveillant_login.html")


# ─────────────────────────────────────────────────────────────────
# ETUDIANT LOGIN — apogée only
# ─────────────────────────────────────────────────────────────────
@require_http_methods(["GET", "POST"])
def etudiant_login(request):
    if request.session.get("etudiant_id"):
        return redirect("portal:etudiant_dashboard")

    if request.method == "POST":
        apogee = request.POST.get("apogee", "").strip().upper()

        if not apogee:
            return render(request, "portal/etudiant_login.html", {
                "error": "Veuillez entrer votre numéro Apogée.",
            })

        try:
            from etudiants.models import Etudiant
            etudiant = Etudiant.objects.get(apogee__iexact=apogee)
        except Exception:
            return render(request, "portal/etudiant_login.html", {
                "error":  "Numéro Apogée introuvable. Vérifiez votre saisie.",
                "apogee": apogee,
            })

        request.session["etudiant_id"]   = etudiant.pk
        request.session["etudiant_name"] = str(etudiant)
        request.session.set_expiry(60 * 60 * 8)
        return redirect("portal:etudiant_dashboard")

    return render(request, "portal/etudiant_login.html")


# ─────────────────────────────────────────────────────────────────
# LOGOUT
# ─────────────────────────────────────────────────────────────────
def surveillant_logout(request):
    logout(request)
    return redirect("portal:surveillant_login")


def etudiant_logout(request):
    request.session.flush()
    return redirect("portal:etudiant_login")


# ─────────────────────────────────────────────────────────────────
# SURVEILLANT DASHBOARD

@login_required(login_url="/portal/surveillant/login/")
def surveillant_dashboard(request):
    if _role(request.user) != "surveillant":
        return redirect("portal:surveillant_login")

    from examens.models import Repartition
    from portal.models import Presence

    surveillant  = request.user.profile.surveillant
    repartitions = Repartition.objects.filter(
        surveillants=surveillant,
        examen__date=date.today(),
    ).select_related("examen", "amphi").prefetch_related("etudiants")

    # Charger les présences existantes pour pré-remplir l'état
    presences = {}
    for rep in repartitions:
        presences[rep.id] = {
            p.etudiant_id: p.present
            for p in Presence.objects.filter(repartition=rep)
        }

    import json
    return render(request, "portal/surveillant_dashboard.html", {
        "user":         request.user,
        "surveillant":  surveillant,
        "repartitions": repartitions,
        "presences_json": json.dumps(presences),
    })
# ─────────────────────────────────────────────────────────────────
# MARK PRESENCE
# ─────────────────────────────────────────────────────────────────
@login_required(login_url="/portal/surveillant/login/")
def mark_presence(request):
    if request.method != "POST":
        return JsonResponse({"error": "Méthode non autorisée."}, status=405)

    try:
        data        = json.loads(request.body)
        rep_id      = int(data["repartition_id"])
        etudiant_id = int(data["etudiant_id"])
        present     = bool(data.get("present", True))
    except (KeyError, ValueError, json.JSONDecodeError):
        return JsonResponse({"error": "Données invalides."}, status=400)

    from examens.models import Repartition
    from portal.models import Presence

    try:
        repartition = Repartition.objects.get(pk=rep_id)
        etudiant    = repartition.etudiants.get(pk=etudiant_id)
    except Exception:
        return JsonResponse({"error": "Étudiant ou répartition introuvable."}, status=404)

    surveillant = request.user.profile.surveillant
    if not repartition.surveillants.filter(pk=surveillant.pk).exists():
        return JsonResponse({"error": "Accès non autorisé."}, status=403)

    presence, _ = Presence.objects.update_or_create(
        repartition=repartition,
        etudiant=etudiant,
        defaults={"present": present, "scanne_par": surveillant},
    )

    return JsonResponse({
        "ok":      True,
        "present": presence.present,
        "nom":     str(etudiant),
    })


# ─────────────────────────────────────────────────────────────────
# ETUDIANT DASHBOARD
# ─────────────────────────────────────────────────────────────────
def etudiant_dashboard(request):
    etudiant_id = request.session.get("etudiant_id")
    if not etudiant_id:
        return redirect("portal:etudiant_login")

    from etudiants.models import Etudiant
    from examens.models import Repartition, Examen

    try:
        etudiant = Etudiant.objects.select_related("annee").get(pk=etudiant_id)
    except Etudiant.DoesNotExist:
        request.session.flush()
        return redirect("portal:etudiant_login")

    examens_qs = Examen.objects.filter(
        niveau=etudiant.niveau,
        annee=etudiant.annee,
    ).select_related("session").order_by("date", "heure_debut")

    today = date.today()
    examens_data = []

    for examen in examens_qs:
        repartition = Repartition.objects.filter(
            examen=examen,
            etudiants=etudiant,
        ).select_related("amphi").first()

        numero_siege = None
        if repartition:
            from examens.models import RepartitionSeat
            assignment = RepartitionSeat.objects.filter(
                repartition=repartition,
                etudiant=etudiant
            ).first()
            numero_siege = assignment.numero if assignment else None

        examens_data.append({
            "examen":       examen,
            "repartition":  repartition,
            "numero_siege": numero_siege,
            "is_today":     examen.date == today,
        })

    return render(request, "portal/etudiant_dashboard.html", {
        "etudiant":      etudiant,
        "examens":       examens_data,
        "examens_count": len(examens_data),
    })


# ─────────────────────────────────────────────────────────────────
# HELPER
# ─────────────────────────────────────────────────────────────────
def _role(user):
    return getattr(getattr(user, "profile", None), "role", None)

@login_required(login_url="/portal/surveillant/login/")
def scan_seat(request):
    if request.method != "POST":
        return JsonResponse({"error": "Méthode non autorisée."}, status=405)

    try:
        data        = json.loads(request.body)
        seat_number = int(data["seat_number"])
    except (KeyError, ValueError, json.JSONDecodeError):
        return JsonResponse({"error": "Données invalides."}, status=400)

    from examens.models import RepartitionSeat
    from portal.models import Presence

    surveillant = request.user.profile.surveillant

    # Cherche l'assignation par numéro de siège pour l'examen d'aujourd'hui
    assignment = RepartitionSeat.objects.filter(
        seat__seat_number=seat_number,
        repartition__examen__date=date.today(),
        repartition__surveillants=surveillant,
    ).select_related("etudiant", "repartition", "seat__amphi").first()

    if not assignment:
        return JsonResponse({
            "error": f"Aucun étudiant assigné au siège {seat_number} pour aujourd'hui."
        }, status=404)

    presence, _ = Presence.objects.update_or_create(
        repartition=assignment.repartition,
        etudiant=assignment.etudiant,
        defaults={"present": True, "scanne_par": surveillant},
    )

    return JsonResponse({
        "ok":          True,
        "nom":         str(assignment.etudiant),
        "etudiant_id": assignment.etudiant.pk,
        "rep_id":      assignment.repartition.pk,
        "seat":        seat_number,
    })