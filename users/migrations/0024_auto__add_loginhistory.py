# encoding: utf-8
import datetime
from south.db import db
from south.v2 import SchemaMigration
from django.db import models

class Migration(SchemaMigration):

    def forwards(self, orm):
        
        # Adding model 'LoginHistory'
        db.create_table('users_loginhistory', (
            ('id', self.gf('django.db.models.fields.AutoField')(primary_key=True)),
            ('type', self.gf('django.db.models.fields.CharField')(max_length=32)),
            ('timestamp', self.gf('django.db.models.fields.DateTimeField')(auto_now_add=True, blank=True)),
            ('user', self.gf('django.db.models.fields.related.ForeignKey')(to=orm['auth.User'])),
        ))
        db.send_create_signal('users', ['LoginHistory'])


    def backwards(self, orm):
        
        # Deleting model 'LoginHistory'
        db.delete_table('users_loginhistory')


    models = {
        'auth.group': {
            'Meta': {'object_name': 'Group'},
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'name': ('django.db.models.fields.CharField', [], {'unique': 'True', 'max_length': '80'}),
            'permissions': ('django.db.models.fields.related.ManyToManyField', [], {'to': "orm['auth.Permission']", 'symmetrical': 'False', 'blank': 'True'})
        },
        'auth.permission': {
            'Meta': {'ordering': "('content_type__app_label', 'content_type__model', 'codename')", 'unique_together': "(('content_type', 'codename'),)", 'object_name': 'Permission'},
            'codename': ('django.db.models.fields.CharField', [], {'max_length': '100'}),
            'content_type': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['contenttypes.ContentType']"}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '50'})
        },
        'auth.user': {
            'Meta': {'object_name': 'User'},
            'date_joined': ('django.db.models.fields.DateTimeField', [], {'default': 'datetime.datetime.now'}),
            'email': ('django.db.models.fields.EmailField', [], {'max_length': '75', 'blank': 'True'}),
            'first_name': ('django.db.models.fields.CharField', [], {'max_length': '30', 'blank': 'True'}),
            'groups': ('django.db.models.fields.related.ManyToManyField', [], {'to': "orm['auth.Group']", 'symmetrical': 'False', 'blank': 'True'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'is_active': ('django.db.models.fields.BooleanField', [], {'default': 'True'}),
            'is_staff': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'is_superuser': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'last_login': ('django.db.models.fields.DateTimeField', [], {'default': 'datetime.datetime.now'}),
            'last_name': ('django.db.models.fields.CharField', [], {'max_length': '30', 'blank': 'True'}),
            'password': ('django.db.models.fields.CharField', [], {'max_length': '128'}),
            'user_permissions': ('django.db.models.fields.related.ManyToManyField', [], {'to': "orm['auth.Permission']", 'symmetrical': 'False', 'blank': 'True'}),
            'username': ('django.db.models.fields.CharField', [], {'unique': 'True', 'max_length': '30'})
        },
        'contenttypes.contenttype': {
            'Meta': {'ordering': "('name',)", 'unique_together': "(('app_label', 'model'),)", 'object_name': 'ContentType', 'db_table': "'django_content_type'"},
            'app_label': ('django.db.models.fields.CharField', [], {'max_length': '100'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'model': ('django.db.models.fields.CharField', [], {'max_length': '100'}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '100'})
        },
        'users.invitation': {
            'Meta': {'object_name': 'Invitation'},
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'is_accepted': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'user': ('django.db.models.fields.related.ForeignKey', [], {'related_name': "'ecs_invitations'", 'to': "orm['auth.User']"}),
            'uuid': ('django.db.models.fields.CharField', [], {'default': "'e91fea12fbb74ce8b2d472a1979d8a61'", 'unique': 'True', 'max_length': '32'})
        },
        'users.loginhistory': {
            'Meta': {'object_name': 'LoginHistory'},
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'timestamp': ('django.db.models.fields.DateTimeField', [], {'auto_now_add': 'True', 'blank': 'True'}),
            'type': ('django.db.models.fields.CharField', [], {'max_length': '32'}),
            'user': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['auth.User']"})
        },
        'users.userprofile': {
            'Meta': {'object_name': 'UserProfile'},
            'address1': ('django.db.models.fields.CharField', [], {'max_length': '60', 'blank': 'True'}),
            'address2': ('django.db.models.fields.CharField', [], {'max_length': '60', 'blank': 'True'}),
            'city': ('django.db.models.fields.CharField', [], {'max_length': '80', 'blank': 'True'}),
            'communication_proxy': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['auth.User']", 'null': 'True'}),
            'fax': ('django.db.models.fields.CharField', [], {'max_length': '45', 'blank': 'True'}),
            'forward_messages_after_minutes': ('django.db.models.fields.PositiveIntegerField', [], {'default': '0'}),
            'gender': ('django.db.models.fields.CharField', [], {'max_length': '1'}),
            'iban': ('django.db.models.fields.CharField', [], {'max_length': '40', 'blank': 'True'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'is_board_member': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'is_executive_board_member': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'is_expedited_reviewer': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'is_help_writer': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'is_indisposed': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'is_insurance_reviewer': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'is_internal': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'is_phantom': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'is_resident_member': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'is_testuser': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'is_thesis_reviewer': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'jobtitle': ('django.db.models.fields.CharField', [], {'max_length': '130', 'blank': 'True'}),
            'last_password_change': ('django.db.models.fields.DateTimeField', [], {'default': 'datetime.datetime.now'}),
            'organisation': ('django.db.models.fields.CharField', [], {'max_length': '180', 'blank': 'True'}),
            'phone': ('django.db.models.fields.CharField', [], {'max_length': '50', 'blank': 'True'}),
            'session_key': ('django.db.models.fields.CharField', [], {'max_length': '40', 'null': 'True'}),
            'single_login_enforced': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'social_security_number': ('django.db.models.fields.CharField', [], {'max_length': '10', 'blank': 'True'}),
            'start_workflow': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'swift_bic': ('django.db.models.fields.CharField', [], {'max_length': '11', 'blank': 'True'}),
            'title': ('django.db.models.fields.CharField', [], {'max_length': '30', 'blank': 'True'}),
            'user': ('django.db.models.fields.related.OneToOneField', [], {'related_name': "'ecs_profile'", 'unique': 'True', 'to': "orm['auth.User']"}),
            'zip_code': ('django.db.models.fields.CharField', [], {'max_length': '10', 'blank': 'True'})
        },
        'users.usersettings': {
            'Meta': {'object_name': 'UserSettings'},
            'communication_filter': ('django.db.models.fields.TextField', [], {}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'pdfviewer_settings': ('django.db.models.fields.TextField', [], {}),
            'submission_filter_all': ('django.db.models.fields.TextField', [], {}),
            'submission_filter_assigned': ('django.db.models.fields.TextField', [], {}),
            'submission_filter_mine': ('django.db.models.fields.TextField', [], {}),
            'submission_filter_search': ('django.db.models.fields.TextField', [], {}),
            'submission_filter_widget': ('django.db.models.fields.TextField', [], {}),
            'submission_filter_widget_internal': ('django.db.models.fields.TextField', [], {}),
            'task_filter': ('django.db.models.fields.TextField', [], {'null': 'True'}),
            'user': ('django.db.models.fields.related.OneToOneField', [], {'related_name': "'ecs_settings'", 'unique': 'True', 'to': "orm['auth.User']"}),
            'useradministration_filter': ('django.db.models.fields.TextField', [], {})
        }
    }

    complete_apps = ['users']
