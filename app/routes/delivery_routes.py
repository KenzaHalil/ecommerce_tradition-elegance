from flask import Blueprint, render_template, request
from app.models import Delivery

bp = Blueprint('delivery_bp', __name__, url_prefix='/delivery')

@bp.route('/track', methods=['GET', 'POST'])
def track():
    query = request.values.get('tracking_number', '').strip()
    delivery = None
    error = None
    if request.method == 'POST' or query:
        if not query:
            error = "Veuillez saisir un numéro de suivi."
        else:
            delivery = Delivery.query.filter_by(tracking_number=query).first()
            if not delivery:
                error = "Aucune livraison trouvée pour ce numéro de suivi."
    return render_template('delivery/track.html', delivery=delivery, query=query, error=error)