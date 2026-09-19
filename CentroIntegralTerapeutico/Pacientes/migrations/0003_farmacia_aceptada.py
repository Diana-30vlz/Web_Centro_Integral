from django.db import migrations, models


def marcar_farmacias_existentes(apps, schema_editor):
    FarmaciaProfile = apps.get_model('Pacientes', 'FarmaciaProfile')
    FarmaciaProfile.objects.all().update(aceptada=True)


class Migration(migrations.Migration):

    dependencies = [
        ('Pacientes', '0002_alcance_por_doctor'),
    ]

    operations = [
        migrations.AddField(
            model_name='farmaciaprofile',
            name='aceptada',
            field=models.BooleanField(
                default=False,
                help_text='La farmacia no puede entrar al sistema hasta que el doctor acepte la relación.',
                verbose_name='Aceptada por el doctor',
            ),
        ),
        migrations.RunPython(marcar_farmacias_existentes, migrations.RunPython.noop),
    ]
