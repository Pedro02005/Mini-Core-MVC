from decimal import Decimal
from io import StringIO

from django.core.management import call_command
from django.test import TestCase
from django.utils import timezone

from .models import Regla, Vendedor, Venta


class DemoTests(TestCase):
    def setUp(self):
        call_command('seed_demo', stdout=StringIO())

    def test_seed_covers_six_months_and_does_not_duplicate_data(self):
        self.assertEqual(Vendedor.objects.count(), 6)
        self.assertEqual(Regla.objects.count(), 6)
        self.assertEqual(Regla.objects.filter(activa=True).count(), 5)
        self.assertEqual(Venta.objects.count(), 144)
        meses = {(venta.fecha_venta.year, venta.fecha_venta.month) for venta in Venta.objects.all()}
        self.assertEqual(len(meses), 6)
        self.assertFalse(Venta.objects.filter(fecha_venta__gt=timezone.localdate()).exists())
        call_command('seed_demo', stdout=StringIO())
        self.assertEqual(Venta.objects.count(), 144)

    def test_commission_thresholds_ignore_inactive_rule(self):
        venta = Venta.objects.first()
        for monto, comision in [('75', '0'), ('100', '2'), ('500', '25'),
                                ('1000', '80'), ('2000', '200'), ('5000', '600')]:
            with self.subTest(monto=monto):
                venta.monto = Decimal(monto)
                self.assertEqual(venta.calcular_comision()['comision'], Decimal(comision))

    def test_sales_crud_and_period_report(self):
        vendedor = Vendedor.objects.first()
        fecha = timezone.localdate().isoformat()
        respuesta = self.client.post('/api/ventas/', {
            'vendedor': vendedor.pk, 'fecha_venta': fecha, 'monto': '1000.00'
        }, content_type='application/json')
        self.assertEqual(respuesta.status_code, 201)
        self.assertEqual(respuesta.json()['comision_calculada']['monto'], 80.0)
        reporte = self.client.post('/api/comisiones/calcular/', {
            'fecha_inicio': '2000-01-01', 'fecha_fin': fecha
        }, content_type='application/json')
        self.assertEqual(reporte.status_code, 200)
        self.assertEqual(reporte.json()['total_ventas'], 145)
        self.assertEqual(reporte.json()['total_vendedores'], 6)
        eliminado = self.client.delete(f"/api/ventas/{respuesta.json()['id']}/")
        self.assertEqual(eliminado.status_code, 204)

    def test_existing_data_is_preserved(self):
        Venta.objects.all().delete()
        call_command('seed_demo', stdout=StringIO())
        self.assertEqual(Venta.objects.count(), 0)
        self.assertEqual(Vendedor.objects.count(), 6)
