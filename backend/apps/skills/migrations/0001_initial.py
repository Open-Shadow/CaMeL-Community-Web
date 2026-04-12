# Generated manually for clean-slate skills package model

import django.contrib.postgres.fields
import django.db.models.deletion
from django.conf import settings
from django.db import migrations, models


class Migration(migrations.Migration):

    initial = True

    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.CreateModel(
            name='Skill',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('name', models.CharField(max_length=80)),
                ('slug', models.SlugField(max_length=100, unique=True)),
                ('description', models.CharField(max_length=500)),
                ('category', models.CharField(choices=[('CODE_DEV', '代码开发'), ('WRITING', '文案写作'), ('DATA_ANALYTICS', '数据分析'), ('ACADEMIC', '学术研究'), ('TRANSLATION', '翻译本地化'), ('CREATIVE', '创意设计'), ('AGENT', 'Agent 工具'), ('PRODUCTIVITY', '办公效率'), ('MISC', '其他')], max_length=30)),
                ('tags', django.contrib.postgres.fields.ArrayField(base_field=models.CharField(max_length=50), default=list, size=10)),
                ('pricing_model', models.CharField(choices=[('FREE', '免费'), ('PAID', '付费')], default='FREE', max_length=10)),
                ('price', models.DecimalField(blank=True, decimal_places=2, max_digits=6, null=True)),
                ('status', models.CharField(choices=[('DRAFT', '草稿'), ('SCANNING', '扫描中'), ('APPROVED', '已上架'), ('REJECTED', '已拒绝'), ('ARCHIVED', '已归档')], default='DRAFT', max_length=20)),
                ('is_featured', models.BooleanField(default=False)),
                ('current_version', models.IntegerField(default=1)),
                ('total_calls', models.IntegerField(default=0)),
                ('avg_rating', models.DecimalField(decimal_places=2, default=0, max_digits=3)),
                ('review_count', models.IntegerField(default=0)),
                ('rejection_reason', models.TextField(blank=True)),
                ('package_file', models.FileField(blank=True, upload_to='skill_packages/%Y/%m/')),
                ('package_sha256', models.CharField(blank=True, max_length=64)),
                ('package_size', models.IntegerField(default=0)),
                ('readme_html', models.TextField(blank=True)),
                ('download_count', models.IntegerField(default=0)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('updated_at', models.DateTimeField(auto_now=True)),
                ('creator', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='skills', to=settings.AUTH_USER_MODEL)),
            ],
            options={
                'db_table': 'skills_skill',
            },
        ),
        migrations.AddIndex(
            model_name='skill',
            index=models.Index(fields=['status', 'category'], name='skills_skil_status_41e488_idx'),
        ),
        migrations.AddIndex(
            model_name='skill',
            index=models.Index(fields=['creator', 'status'], name='skills_skil_creator_3b2d7c_idx'),
        ),
        migrations.CreateModel(
            name='SkillVersion',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('version', models.CharField(max_length=20)),
                ('package_file', models.FileField(upload_to='skill_packages/%Y/%m/')),
                ('package_sha256', models.CharField(max_length=64)),
                ('changelog', models.TextField(blank=True)),
                ('status', models.CharField(choices=[('SCANNING', '扫描中'), ('APPROVED', '已通过'), ('REJECTED', '已拒绝'), ('ARCHIVED', '已归档')], default='SCANNING', max_length=20)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('skill', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='versions', to='skills.skill')),
            ],
            options={
                'db_table': 'skills_skill_version',
                'unique_together': {('skill', 'version')},
            },
        ),
        migrations.CreateModel(
            name='SkillCall',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('skill_version', models.CharField(max_length=20)),
                ('input_text', models.TextField()),
                ('output_text', models.TextField(blank=True)),
                ('duration_ms', models.IntegerField(blank=True, null=True)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('caller', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='skill_calls', to=settings.AUTH_USER_MODEL)),
                ('skill', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='calls', to='skills.skill')),
            ],
            options={
                'db_table': 'skills_skill_call',
            },
        ),
        migrations.AddIndex(
            model_name='skillcall',
            index=models.Index(fields=['skill', 'created_at'], name='skills_skil_skill_i_a91847_idx'),
        ),
        migrations.CreateModel(
            name='SkillReview',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('rating', models.IntegerField()),
                ('comment', models.TextField(blank=True)),
                ('tags', django.contrib.postgres.fields.ArrayField(base_field=models.CharField(max_length=30), default=list)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('updated_at', models.DateTimeField(auto_now=True)),
                ('reviewer', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='skill_reviews', to=settings.AUTH_USER_MODEL)),
                ('skill', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='reviews', to='skills.skill')),
            ],
            options={
                'db_table': 'skills_skill_review',
                'unique_together': {('skill', 'reviewer')},
            },
        ),
        migrations.CreateModel(
            name='SkillUsagePreference',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('locked_version', models.CharField(blank=True, default='', max_length=20)),
                ('auto_follow_latest', models.BooleanField(default=True)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('updated_at', models.DateTimeField(auto_now=True)),
                ('user', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='skill_usage_preferences', to=settings.AUTH_USER_MODEL)),
                ('skill', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='usage_preferences', to='skills.skill')),
            ],
            options={
                'db_table': 'skills_skill_usage_preference',
                'unique_together': {('skill', 'user')},
            },
        ),
        migrations.CreateModel(
            name='SkillPurchase',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('paid_amount', models.DecimalField(decimal_places=2, default=0, max_digits=6)),
                ('payment_type', models.CharField(max_length=10)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('user', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='skill_purchases', to=settings.AUTH_USER_MODEL)),
                ('skill', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='purchases', to='skills.skill')),
            ],
            options={
                'db_table': 'skills_skill_purchase',
                'unique_together': {('skill', 'user')},
            },
        ),
        migrations.CreateModel(
            name='SkillReport',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('reason', models.CharField(choices=[('MALICIOUS_CODE', '恶意代码'), ('FALSE_DESCRIPTION', '虚假描述'), ('COPYRIGHT', '侵权'), ('OTHER', '其他')], max_length=30)),
                ('detail', models.TextField(blank=True)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('reporter', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='skill_reports', to=settings.AUTH_USER_MODEL)),
                ('skill', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='reports', to='skills.skill')),
            ],
            options={
                'db_table': 'skills_skill_report',
                'unique_together': {('skill', 'reporter')},
            },
        ),
    ]
