from datetime import timedelta
from django.utils.timezone import now
from django.db.models import (
    ExpressionWrapper, F, DurationField, Sum, Count, Q,
    Value, CharField, FloatField, Case, When, IntegerField
)
from django.db.models.functions import TruncDate, Concat, Coalesce
from plotly import express as px
from todo.models import SuiviTache, TacheSelectionnee
from authentication.models import User
import humanize

humanize.activate('fr_FR')

def format_duree(seconds):
    """Convertit les secondes en format HH:MM."""
    seconds = seconds or 0
    hours = int(seconds // 3600)
    minutes = int((seconds % 3600) // 60)
    return f"{hours:02d}h{minutes:02d}"

def generate_graphs(user_id=None, period='30j'):
    end_date = now().date()
    start_date = end_date - timedelta(days=30)

    base_filter = Q(date_selection__range=[start_date, end_date]) & ~Q(user__role='admin')
    if user_id and user_id != 'all':
        base_filter &= Q(user_id=user_id)

    def graph_temps_activite():
        queryset = SuiviTache.objects.filter(
            start_time__date__range=[start_date, end_date],
            end_time__isnull=False
        ).exclude(user__role='admin')

        if user_id and user_id != 'all':
            queryset = queryset.filter(user_id=user_id)

        data = list(queryset.annotate(
            duree_sec=ExpressionWrapper(
                F('end_time') - F('start_time'),
                output_field=DurationField()
            )
        ).values('user__first_name', 'user__last_name')
         .annotate(total_sec=Sum('duree_sec'))
         .order_by('-total_sec'))

        if not data:
            return px.bar(
                title="Temps d'activité (30 derniers jours)",
                labels={'heures': 'Heures', 'nom_complet': 'Employé'}
            ).update_layout(annotations=[{
                'text': 'Aucune donnée disponible',
                'xref': 'paper',
                'yref': 'paper',
                'showarrow': False,
                'font': {'size': 20}
            }])

        for item in data:
            sec = item['total_sec'].total_seconds() if item['total_sec'] else 0
            item['nom_complet'] = f"{item['user__first_name']} {item['user__last_name']}"
            item['duree'] = format_duree(sec)
            item['heures'] = sec / 3600

        fig = px.bar(
            data,
            x='heures',
            y='nom_complet',
            orientation='h',
            text='duree',
            title="Temps d'activité (30 derniers jours)",
            labels={'nom_complet': 'Employé', 'heures': 'Heures'}
        )
        fig.update_traces(texttemplate='%{text}', textposition='outside')
        fig.update_layout(yaxis={'categoryorder': 'total descending'})
        return fig

    def graph_top10_taches():
        queryset = SuiviTache.objects.filter(
            start_time__date__range=[start_date, end_date],
            end_time__isnull=False
        ).exclude(user__role='admin')

        if user_id and user_id != 'all':
            queryset = queryset.filter(user_id=user_id)

        data = list(queryset.annotate(
            duree_sec=ExpressionWrapper(
                F('end_time') - F('start_time'),
                output_field=DurationField()
            )
        ).values('tache__titre')
         .annotate(total_sec=Sum('duree_sec'))
         .order_by('-total_sec')[:10])

        if not data:
            return px.bar(
                title="Top 10 tâches les plus longues"
            ).update_layout(annotations=[{
                'text': 'Aucune donnée disponible',
                'xref': 'paper',
                'yref': 'paper',
                'showarrow': False,
                'font': {'size': 20}
            }])

        for item in data:
            sec = item['total_sec'].total_seconds() if item['total_sec'] else 0
            item['duree'] = format_duree(sec)
            item['heures'] = sec / 3600

        fig = px.bar(
            data,
            x='heures',
            y='tache__titre',
            orientation='h',
            text='duree',
            title="Top 10 tâches les plus longues",
            labels={'tache__titre': 'Tâche'}
        )
        fig.update_traces(texttemplate='%{text}', textposition='outside')
        return fig

    def graph_perf_collective():
        stats = TacheSelectionnee.objects.filter(base_filter) \
            .annotate(jour=TruncDate('date_selection')) \
            .values('jour') \
            .annotate(
                total_taches=Count('id', output_field=IntegerField()),
                taches_completees=Count('id', filter=Q(is_done=True), output_field=IntegerField())
            ) \
            .annotate(
                taux_jour=Case(
                    When(total_taches=0, then=Value(0.0, output_field=FloatField())),
                    default=ExpressionWrapper(
                        100.0 * F('taches_completees') / F('total_taches'),
                        output_field=FloatField()
                    )
                )
            ).order_by('jour')

        data = [{'date': s['jour'], 'taux': s['taux_jour']} for s in stats]

        fig = px.line(
            data,
            x='date',
            y='taux',
            title="Performance collective quotidienne",
            labels={'date': 'Date', 'taux': 'Taux de complétion (%)'}
        )
        fig.update_layout(yaxis_range=[0, 110])
        return fig

    def graph_perf_individuelle():
        users = User.objects.exclude(role='admin')
        if not users.exists():
            return px.line(title="Aucun employé à afficher")

        data = []
        for user in users:
            stats = TacheSelectionnee.objects.filter(
                date_selection__range=[start_date, end_date],
                user=user
            ).annotate(jour=TruncDate('date_selection')) \
             .values('jour') \
             .annotate(
                 fait=Count('id', filter=Q(is_done=True), output_field=IntegerField()),
                 total=Count('id', output_field=IntegerField())
             ).annotate(
                 taux=ExpressionWrapper(
                     100.0 * F('fait') / F('total'),
                     output_field=FloatField()
                 )
             ).order_by('jour')

            for s in stats:
                data.append({
                    'date': s['jour'],
                    'taux': s['taux'],
                    'employe': f"{user.first_name} {user.last_name}"
                })

        fig = px.line(
            data,
            x='date',
            y='taux',
            color='employe',
            title="Performances individuelles",
            labels={'date': 'Date', 'taux': 'Taux (%)', 'employe': 'Employé'}
        )
        fig.update_layout(yaxis_range=[0, 110])
        return fig

    return {
        'graph_activite': graph_temps_activite().to_html(),
        'graph_top10': graph_top10_taches().to_html(),
        'graph_perf_collective': graph_perf_collective().to_html(),
        'graph_perf_individuelle': graph_perf_individuelle().to_html()
    }