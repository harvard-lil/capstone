from django.db import models


class UserHistory(models.Model):
    """
    If user has opted in, record each full-text case access.
    """
    id = models.BigAutoField(primary_key=True)
    user_id = models.PositiveIntegerField()  # not foreign key because this refers to another database
    case_id = models.PositiveIntegerField()  # not foreign key because this refers to another database
    date = models.DateTimeField(auto_now_add=True)

    class Meta:
        indexes = [
            models.Index(fields=['user_id', 'case_id']),
            models.Index(fields=['user_id', '-date']),
        ]
        ordering = ['user_id', '-date', 'case_id']
