import pytest
from datetime import datetime
from app import models

def test_create_order_payment_delivery_via_orm(ctx):
    # create a user (some tables expect a user)
    u = models.User(email="test@example.com", password_hash="x")
    models.db.session.add(u)
    models.db.session.flush()

    # create an order marked as paid
    order = models.Order(user_id=u.id, status="PAYEE", total_cents=12345, created_at=datetime.utcnow(), paid_at=datetime.utcnow())
    models.db.session.add(order)
    models.db.session.flush()

    # create payment
    payment = models.Payment(order_id=order.id, user_id=u.id, amount_cents=12345, provider="manual", succeeded=True, created_at=datetime.utcnow())
    models.db.session.add(payment)

    # create delivery with tracking
    delivery = models.Delivery(order_id=order.id, carrier="TestCarrier", tracking_number="TRKTEST123", status="pending", updated_at=datetime.utcnow().isoformat())
    models.db.session.add(delivery)

    models.db.session.commit()

    # verify persisted
    o = models.Order.query.get(order.id)
    assert o is not None and o.status == "PAYEE"
    p = models.Payment.query.filter_by(order_id=order.id).first()
    assert p is not None and p.succeeded is True
    d = models.Delivery.query.filter_by(order_id=order.id).first()
    assert d is not None and d.tracking_number == "TRKTEST123"

def test_delivery_track_route_returns_tracking(client, ctx):
    # insert a delivery row
    from app import models
    u = models.User(email="viewer@example.com", password_hash="x")
    models.db.session.add(u)
    models.db.session.flush()
    order = models.Order(user_id=u.id, status="PAYEE", total_cents=1000, created_at=datetime.utcnow(), paid_at=datetime.utcnow())
    models.db.session.add(order)
    models.db.session.flush()
    tn = "TRK-UNIT-TEST-1"
    delivery = models.Delivery(order_id=order.id, carrier="C", tracking_number=tn, status="pending", updated_at=datetime.utcnow().isoformat())
    models.db.session.add(delivery)
    models.db.session.commit()

    # call track endpoint
    r = client.get(f"/delivery/track?tracking_number={tn}")
    assert r.status_code == 200
    assert tn.encode() in r.data  # page contains the tracking number