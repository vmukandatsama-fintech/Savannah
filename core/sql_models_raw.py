# This is an auto-generated Django model module.
# You'll have to do the following manually to clean this up:
#   * Rearrange models' order
#   * Make sure each model has one field with primary_key=True
#   * Make sure each ForeignKey and OneToOneField has `on_delete` set to the desired behavior
#   * Remove `managed = False` lines if you wish to allow Django to create, modify, and delete the table
# Feel free to rename the models, but don't rename db_table values or field names.
from django.db import models


class Departments(models.Model):
    departmentid = models.AutoField(db_column='DepartmentID')  # Field name made lowercase.
    departmentcode = models.CharField(db_column='DepartmentCode', primary_key=True, max_length=50, db_collation='Latin1_General_CI_AS')  # Field name made lowercase.
    name = models.CharField(db_column='Name', max_length=255, db_collation='Latin1_General_CI_AS')  # Field name made lowercase.
    isactive = models.BooleanField(db_column='IsActive', blank=True, null=True)  # Field name made lowercase.
    authrequired = models.BooleanField(db_column='AuthRequired', blank=True, null=True)  # Field name made lowercase.
    createdat = models.DateTimeField(db_column='CreatedAt', blank=True, null=True)  # Field name made lowercase.

    class Meta:
        managed = False
        db_table = 'departments'
