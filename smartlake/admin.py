from django.contrib import admin
from .models import *
import datetime
from django.contrib import messages
from django.core.exceptions import ValidationError
from .forms import TableMetadataForm
from django.http import HttpResponseRedirect
from django.urls import path
from django.shortcuts import render
from .forms import *
from .utils.get_metadata import get_or_create_table_metadata
from django.http import JsonResponse




class BaseAdmin(admin.ModelAdmin):
    def __init__(self, model, admin_site):
        all_fields = [field.name for field in model._meta.fields]
        list_display_priority_fields = ['mod_dtm', 'id_mod_user']
        list_display_not_fields = ['spark_query','sql_where'] + list_display_priority_fields
        self.list_display = [
            field for field in all_fields if field not in list_display_not_fields] + list_display_priority_fields
        self.fields = [field for field in all_fields if field not in [
            'id', 'mod_dtm', 'id_mod_user']]       
        
        super().__init__(model, admin_site)

    def save_model(self, request, obj, form, change):
        obj.id_mod_user = request.user
        obj.mod_dtm = datetime.datetime.now()
        obj.save()

@admin.register(Project)
class ProjectAdmin(BaseAdmin):
    list_display_links = ['project_cd','project_name']
    search_fields = ('project_cd','project_name',)
    list_filter = ('project_cd','project_name',)


@admin.register(DbEnv)
class DbEnvAdmin(BaseAdmin):
    list_display_links = ['db_env_name']
    search_fields = ('db_env_name',)
    list_filter = ('db_env_name',)


@admin.register(DatabaseType)
class DatabaseTypeAdmin(BaseAdmin):
    list_display_links = ['db_type_name']
    search_fields = ('db_type_name',)
    list_filter = ('db_type_name',)


@admin.register(Databases)
class DatabasesAdmin(BaseAdmin):
    list_display_links = ['db_name']
    search_fields = ('db_name', 'db_type')
    list_filter = ('mod_dtm', 'id_dbenv')

    def save_model(self, request, obj, form, change):

        if change == False :
            obj.backup_bucket = f"s3-datalake-{obj.id_dbenv.db_env_name.lower()}-{obj.id_project.project_cd.lower()}-backup-table"
            obj.iceberg_bucket = f"s3-datalake-{obj.id_dbenv.db_env_name.lower()}-{obj.id_project.project_cd.lower()}-iceberg-table"

        super().save_model(request, obj, form, change)

@admin.register(PartitionType)
class PartitionTypeAdmin(BaseAdmin):
    list_display_links = ['partition_type']
    search_fields = ('partition_type',)
    list_filter = ('partition_type',)


@admin.register(LoadInterval)
class LoadIntervalAdmin(BaseAdmin):
    list_display_links = ['interval_type',]
    search_fields = ('interval_type',)
    list_filter = ('interval_type',)


@admin.register(LoadMethod)
class LoadMethodAdmin(BaseAdmin):
    list_display_links = ['load_type',]
    search_fields = ('load_type',)
    list_filter = ('load_type',)


class ColumnsInline(admin.TabularInline):
    model = Columns
    extra = 1
    exclude = ['mod_dtm', 'id_mod_user']


@admin.register(Tables)
class TablesAdmin(BaseAdmin):
    list_display_links = ['table_name']
    search_fields = ('table_name',)
    list_filter = ('use_yn', 'id_db', 'id_load_interval', 'id_load_method', 'cdc_yn')

    inlines = [ColumnsInline]

    def save_related(self, request, form, formsets, change):
        form.save(commit=False)

        has_primary_key = False
        for formset in formsets:
            instances = formset.save(commit=False)
            # 삭제된 객체 처리
            for deleted_instance in formset.deleted_objects:
                deleted_instance.delete()
            for instance in instances:
                instance.column_name = instance.column_name.lower()
                if instance.pk_yn == 'Y':
                    has_primary_key = True
                instance.id_mod_user = request.user
                instance.mod_dtm = datetime.datetime.now()
                instance.save()
            formset.save_m2m()

        has_primary_key = Columns.objects.filter(
            id_table=form.instance, pk_yn='Y').exists()

        if not has_primary_key:
            messages.error(
                request, f"DB '{form.instance.id_db.db_name}'의 테이블 '{form.instance.table_name}'에 Primary Key가 지정되지 않았습니다. 확인하세요.")

        form.save_m2m()

    def save_model(self, request, obj, form, change):
        # 테이블 이름을 소문자로 저장
        obj.table_name = obj.table_name.lower()
        obj.id_mod_user = request.user
        obj.mod_dtm = datetime.datetime.now()

        if change == False :
            obj.catalog_db_name = obj.id_db.db_name.lower()
            obj.catalog_table_name = obj.table_name.replace(".", "__")

        # 중복 체크: 동일한 데이터베이스와 테이블 이름이 있는지 확인
        if Tables.objects.filter(id_db=obj.id_db, table_name=obj.table_name).exclude(pk=obj.pk).exists():
            messages.error(request, f"DB '{obj.id_db.db_name}'에 테이블 '{obj.table_name}'이(가) 이미 존재합니다. 중복된 테이블은 저장할 수 없습니다.")
            return  # 중복이 있으면 저장하지 않음

        super().save_model(request, obj, form, change)
        
        try:
            # 이미 저장된 컬럼이 없다면.
            if Columns.objects.filter(id_table=obj.id).exists() == False:
                db_id = obj.id_db.id
                table_name = obj.table_name            
                # 테이블 메타데이터 저장: 테이블 저장 후 메타데이터 저장 함수 호출
                get_or_create_table_metadata(db_id, obj.id, table_name)
                messages.success(request, f"테이블 '{table_name}'에 대한 메타데이터가 저장되었습니다.")
        except Exception as e:
            messages.error(request, f"메타데이터 저장 중 오류 발생: {str(e)}")

# @admin.register(DataTypes)
# class DataTypesAdmin(BaseAdmin):
#     list_display_links = ['datatype_name']
#     search_fields = ('datatype_name',)
    


# @admin.register(DataTypesMapping)
# class DataTypesMappingAdmin(BaseAdmin):
#     list_display_links = ['datatype_mapping_name']
#     search_fields = ('datatype_mapping_name',)
    


# @admin.register(Columns)
# class ColumnsAdmin(BaseAdmin):
#     list_display_links = ['column_name']
#     search_fields = ('column_name',)
    
