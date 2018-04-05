class FalconRouter(object):
    """
    A router to control all database operations on models in the
    falcon application.
    """
    def db_for_read(self, model, **hints):
        """
        Attempts to read falcon models go to falcon_db.
        """
        if model._meta.app_label == 'falcon':
            return 'falcon_db'
        return None

    def db_for_write(self, model, **hints):
        """
        Attempts to write falcon models go to falcon_db.
        """
        if model._meta.app_label == 'falcon':
            return 'falcon_db'
        return None

    def allow_relation(self, obj1, obj2, **hints):
        """
        Allow relations if a model in the falcon app is involved.
        """
        if obj1._meta.app_label == 'falcon' or \
           obj2._meta.app_label == 'falcon':
           return True
        return None

    def allow_migrate(self, db, app_label, model_name=None, **hints):
        """
        Prevent migration to falcon_db and migration of falcon models
        """
        if app_label == 'falcon':
            return False
        if db == 'falcon_db':
            return False
        return None
