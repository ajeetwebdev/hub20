# Generated by Django 3.2.3 on 2021-06-05 09:15

from django.conf import settings
import django.contrib.postgres.fields
from django.db import migrations, models
import django.db.models.deletion
import django.utils.timezone
import hub20.apps.blockchain.fields
import hub20.apps.ethereum_money.models
import model_utils.fields


class Migration(migrations.Migration):

    initial = True

    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
        ('blockchain', '0001_initial'),
        ('ethereum_money', '0001_initial'),
    ]

    operations = [
        migrations.CreateModel(
            name='Raiden',
            fields=[
                ('baseethereumaccount_ptr', models.OneToOneField(auto_created=True, on_delete=django.db.models.deletion.CASCADE, parent_link=True, primary_key=True, serialize=False, to='blockchain.baseethereumaccount')),
            ],
            bases=('blockchain.baseethereumaccount',),
        ),
        migrations.CreateModel(
            name='RaidenManagementOrder',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('created', model_utils.fields.AutoCreatedField(default=django.utils.timezone.now, editable=False, verbose_name='created')),
                ('modified', model_utils.fields.AutoLastModifiedField(default=django.utils.timezone.now, editable=False, verbose_name='modified')),
                ('raiden', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to='raiden.raiden')),
                ('user', models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, to=settings.AUTH_USER_MODEL)),
            ],
            options={
                'abstract': False,
            },
        ),
        migrations.CreateModel(
            name='TokenNetwork',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('address', hub20.apps.blockchain.fields.EthereumAddressField()),
                ('token', models.OneToOneField(on_delete=django.db.models.deletion.CASCADE, to='ethereum_money.ethereumtoken')),
            ],
        ),
        migrations.CreateModel(
            name='TokenNetworkChannel',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('identifier', hub20.apps.blockchain.fields.Uint256Field()),
                ('participant_addresses', django.contrib.postgres.fields.ArrayField(base_field=hub20.apps.blockchain.fields.EthereumAddressField(), size=2)),
                ('token_network', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='channels', to='raiden.tokennetwork')),
            ],
        ),
        migrations.CreateModel(
            name='TokenNetworkChannelStatus',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('status', model_utils.fields.StatusField(choices=[('opened', 'opened'), ('settling', 'settling'), ('settled', 'settled'), ('unusable', 'unusable'), ('closed', 'closed'), ('closing', 'closing')], default='opened', max_length=100, no_check_for_status=True, verbose_name='status')),
                ('status_changed', model_utils.fields.MonitorField(default=django.utils.timezone.now, monitor='status', verbose_name='status changed')),
                ('channel', models.OneToOneField(on_delete=django.db.models.deletion.CASCADE, related_name='status', to='raiden.tokennetworkchannel')),
            ],
            options={
                'abstract': False,
            },
        ),
        migrations.CreateModel(
            name='RaidenManagementOrderResult',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('created', model_utils.fields.AutoCreatedField(default=django.utils.timezone.now, editable=False, verbose_name='created')),
                ('modified', model_utils.fields.AutoLastModifiedField(default=django.utils.timezone.now, editable=False, verbose_name='modified')),
                ('order', models.OneToOneField(on_delete=django.db.models.deletion.CASCADE, related_name='result', to='raiden.raidenmanagementorder')),
                ('transaction', models.OneToOneField(null=True, on_delete=django.db.models.deletion.SET_NULL, to='blockchain.transaction')),
            ],
            options={
                'abstract': False,
            },
        ),
        migrations.CreateModel(
            name='RaidenManagementOrderError',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('created', model_utils.fields.AutoCreatedField(default=django.utils.timezone.now, editable=False, verbose_name='created')),
                ('modified', model_utils.fields.AutoLastModifiedField(default=django.utils.timezone.now, editable=False, verbose_name='modified')),
                ('message', models.TextField(blank=True, null=True)),
                ('order', models.OneToOneField(on_delete=django.db.models.deletion.CASCADE, related_name='error', to='raiden.raidenmanagementorder')),
                ('transaction', models.OneToOneField(null=True, on_delete=django.db.models.deletion.SET_NULL, to='blockchain.transaction')),
            ],
            options={
                'abstract': False,
            },
        ),
        migrations.CreateModel(
            name='Channel',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('status', model_utils.fields.StatusField(choices=[('opened', 'opened'), ('settling', 'settling'), ('settled', 'settled'), ('unusable', 'unusable'), ('closed', 'closed'), ('closing', 'closing')], default='opened', max_length=100, no_check_for_status=True, verbose_name='status')),
                ('status_changed', model_utils.fields.MonitorField(default=django.utils.timezone.now, monitor='status', verbose_name='status changed')),
                ('identifier', models.PositiveIntegerField()),
                ('partner_address', hub20.apps.blockchain.fields.EthereumAddressField(db_index=True)),
                ('balance', hub20.apps.ethereum_money.models.EthereumTokenAmountField(decimal_places=18, max_digits=32)),
                ('total_deposit', hub20.apps.ethereum_money.models.EthereumTokenAmountField(decimal_places=18, max_digits=32)),
                ('total_withdraw', hub20.apps.ethereum_money.models.EthereumTokenAmountField(decimal_places=18, max_digits=32)),
                ('raiden', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='channels', to='raiden.raiden')),
                ('token_network', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to='raiden.tokennetwork')),
            ],
            options={
                'unique_together': {('raiden', 'token_network', 'partner_address'), ('raiden', 'token_network', 'identifier')},
            },
        ),
        migrations.CreateModel(
            name='UserDepositContractOrder',
            fields=[
                ('raidenmanagementorder_ptr', models.OneToOneField(auto_created=True, on_delete=django.db.models.deletion.CASCADE, parent_link=True, primary_key=True, serialize=False, to='raiden.raidenmanagementorder')),
                ('amount', hub20.apps.ethereum_money.models.EthereumTokenAmountField(decimal_places=18, max_digits=32)),
                ('currency', models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, to='ethereum_money.ethereumtoken')),
            ],
            options={
                'abstract': False,
            },
            bases=('raiden.raidenmanagementorder', models.Model),
        ),
        migrations.CreateModel(
            name='TokenNetworkChannelEvent',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('name', models.CharField(db_index=True, max_length=32)),
                ('channel', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to='raiden.tokennetworkchannel')),
                ('transaction', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to='blockchain.transaction')),
            ],
            options={
                'unique_together': {('channel', 'transaction')},
            },
        ),
        migrations.CreateModel(
            name='Payment',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('amount', hub20.apps.ethereum_money.models.EthereumTokenAmountField(decimal_places=18, max_digits=32)),
                ('timestamp', models.DateTimeField()),
                ('identifier', hub20.apps.blockchain.fields.Uint256Field()),
                ('sender_address', hub20.apps.blockchain.fields.EthereumAddressField()),
                ('receiver_address', hub20.apps.blockchain.fields.EthereumAddressField()),
                ('channel', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='payments', to='raiden.channel')),
            ],
            options={
                'unique_together': {('channel', 'identifier', 'sender_address', 'receiver_address')},
            },
        ),
        migrations.CreateModel(
            name='LeaveTokenNetworkOrder',
            fields=[
                ('raidenmanagementorder_ptr', models.OneToOneField(auto_created=True, on_delete=django.db.models.deletion.CASCADE, parent_link=True, primary_key=True, serialize=False, to='raiden.raidenmanagementorder')),
                ('token_network', models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, to='raiden.tokennetwork')),
            ],
            options={
                'abstract': False,
            },
            bases=('raiden.raidenmanagementorder',),
        ),
        migrations.CreateModel(
            name='JoinTokenNetworkOrder',
            fields=[
                ('raidenmanagementorder_ptr', models.OneToOneField(auto_created=True, on_delete=django.db.models.deletion.CASCADE, parent_link=True, primary_key=True, serialize=False, to='raiden.raidenmanagementorder')),
                ('amount', hub20.apps.ethereum_money.models.EthereumTokenAmountField(decimal_places=18, max_digits=32)),
                ('token_network', models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, to='raiden.tokennetwork')),
            ],
            options={
                'abstract': False,
            },
            bases=('raiden.raidenmanagementorder',),
        ),
        migrations.CreateModel(
            name='ChannelWithdrawOrder',
            fields=[
                ('raidenmanagementorder_ptr', models.OneToOneField(auto_created=True, on_delete=django.db.models.deletion.CASCADE, parent_link=True, primary_key=True, serialize=False, to='raiden.raidenmanagementorder')),
                ('amount', hub20.apps.ethereum_money.models.EthereumTokenAmountField(decimal_places=18, max_digits=32)),
                ('channel', models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, to='raiden.channel')),
            ],
            options={
                'abstract': False,
            },
            bases=('raiden.raidenmanagementorder',),
        ),
        migrations.CreateModel(
            name='ChannelDepositOrder',
            fields=[
                ('raidenmanagementorder_ptr', models.OneToOneField(auto_created=True, on_delete=django.db.models.deletion.CASCADE, parent_link=True, primary_key=True, serialize=False, to='raiden.raidenmanagementorder')),
                ('amount', hub20.apps.ethereum_money.models.EthereumTokenAmountField(decimal_places=18, max_digits=32)),
                ('channel', models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, to='raiden.channel')),
            ],
            options={
                'abstract': False,
            },
            bases=('raiden.raidenmanagementorder',),
        ),
    ]
