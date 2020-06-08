from django.test import TestCase
from mock import patch, call
from datetime import datetime

from model_mommy import mommy

from backup.tasks import make_databases_backup
from backup.models import Snapshot, BackupGroup
from dbaas.tests.helpers import DatabaseHelper, InfraHelper


FAKE_NOW = datetime(2020, 1, 1, 5, 10, 00)


class FakeDatetime(datetime):
    @staticmethod
    def now():
        return FAKE_NOW


class TestMakeDatabasesBackup(TestCase):

    def setUp(self):
        self.backup_hour = 5
        self.year = 2020
        self.month = 1
        self.day = 1

        mommy.make(
            'Configuration', name='backup_hour', value=str(self.backup_hour)
        )
        mommy.make(
            'Configuration', name='prod_envs', value='prod,prod-cm,aws-prod'
        )
        mommy.make(
            'Configuration', name='dev_envs', value='dev,qa2,aws-dev'
        )
        self.dev_env = mommy.make('Environment', name='dev')
        mommy.make('Environment', name='prod')
        self.infra = InfraHelper.create(
            backup_hour=self.backup_hour,
            plan__has_persistence=True,
            environment=self.dev_env
        )
        self.instance = mommy.make(
            'Instance', databaseinfra=self.infra
        )
        self.database = DatabaseHelper.create(
            databaseinfra=self.infra,
            environment=self.dev_env
        )

    @patch('backup.tasks.make_instance_snapshot_backup')
    @patch('backup.models.BackupGroup.save')
    @patch('backup.tasks.datetime', FakeDatetime)
    @patch('notification.models.TaskHistory.register')
    @patch('backup.tasks.get_worker_name')
    def test_backup_current_hour(
        self, get_worker_name_mock, task_register, save_backup_group,
        make_instance_snapshot_backup
    ):
        get_worker_name_mock.return_value = 'test'
        group = BackupGroup()
        save_backup_group.return_value = group
        make_instance_snapshot_backup.return_value.status.return_value = (
            Snapshot.SUCCESS
        )

        make_databases_backup()
        make_instance_snapshot_backup.assert_called_with(
            current_hour=self.backup_hour, instance=self.instance, error={},
            group=group
        )

    # @patch('backup.tasks.make_instance_snapshot_backup')
    # @patch('backup.models.BackupGroup.save')
    # @patch('notification.models.TaskHistory.register')
    # @patch('backup.tasks.get_worker_name')
    # def test_current_hour_without_pending_backup(
    #     self, get_worker_name_mock, task_register, save_backup_group,
    #     make_instance_snapshot_backup
    # ):
    #     get_worker_name_mock.return_value = 'test'
    #     group = BackupGroup()
    #     save_backup_group.return_value = group
    #     make_instance_snapshot_backup.return_value.status.return_value = (
    #         Snapshot.SUCCESS
    #     )

    @patch('backup.tasks.make_instance_snapshot_backup')
    @patch('backup.models.BackupGroup.save')
    @patch('backup.tasks.datetime', FakeDatetime)
    @patch('notification.models.TaskHistory.register')
    @patch('backup.tasks.get_worker_name')
    def test_current_hour_with_pending_backup(
        self, get_worker_name_mock, task_register, save_backup_group,
        make_instance_snapshot_backup
    ):

        infra_mock = self.infra
        infra_mock.pk = None
        infra_mock.name = 'pending_backup_test'
        infra_mock.backup_hour = self.backup_hour - 1
        infra_mock.environment = self.dev_env
        infra_mock.save()
        print(infra_mock.environment)

        instance_mock = mommy.make(
            'Instance', databaseinfra=infra_mock
        )

        get_worker_name_mock.return_value = 'test'
        group = BackupGroup()
        save_backup_group.return_value = group
        make_instance_snapshot_backup.return_value.status.return_value = (
            Snapshot.SUCCESS
        )

        make_databases_backup()
        calls = [
            call(
                current_hour=self.backup_hour, instance=self.instance,
                error={}, group=group
            ),
            call(
                current_hour=self.backup_hour, instance=instance_mock,
                error={}, group=group
            )
        ]
        make_instance_snapshot_backup.assert_has_calls(calls)

        # make_instance_snapshot_backup.assert_called_with(
        #     current_hour=self.backup_hour, instance=self.instance, error={},
        #     group=group
        # )
