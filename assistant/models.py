from django.db import models


class FAQ(models.Model):
    question = models.CharField(max_length=255, unique=True)
    answer = models.TextField()
    category = models.CharField(max_length=60, default="General", db_index=True)
    keywords = models.CharField(max_length=255, blank=True,
                                help_text="Optional comma-separated synonyms used by the assistant.")
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["category", "id"]
        verbose_name = "FAQ"
        verbose_name_plural = "FAQs"

    def __str__(self):
        return self.question


class ErrorCode(models.Model):
    code = models.PositiveIntegerField(unique=True)
    title = models.CharField(max_length=120)
    description = models.TextField()
    possible_causes = models.TextField()
    recommended_solution = models.TextField()
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["code"]

    def __str__(self):
        return f"{self.code} – {self.title}"


class HelpArticle(models.Model):
    """Inventory application help documentation used by the assistant."""

    title = models.CharField(max_length=160, unique=True)
    keywords = models.CharField(max_length=255, blank=True)
    content = models.TextField()
    is_active = models.BooleanField(default=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["title"]

    def __str__(self):
        return self.title
