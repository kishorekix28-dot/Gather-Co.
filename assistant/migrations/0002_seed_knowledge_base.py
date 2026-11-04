from django.db import migrations


def seed(apps, schema_editor):
    from assistant.seed_data import ERROR_CODES, FAQS, HELP_ARTICLES

    FAQ = apps.get_model("assistant", "FAQ")
    ErrorCode = apps.get_model("assistant", "ErrorCode")
    HelpArticle = apps.get_model("assistant", "HelpArticle")
    for category, question, answer, keywords in FAQS:
        FAQ.objects.update_or_create(question=question, defaults={
            "answer": answer, "category": category, "keywords": keywords, "is_active": True})
    for code, title, description, causes, solution in ERROR_CODES:
        ErrorCode.objects.update_or_create(code=code, defaults={
            "title": title, "description": description, "possible_causes": causes,
            "recommended_solution": solution})
    for title, keywords, content in HELP_ARTICLES:
        HelpArticle.objects.update_or_create(title=title, defaults={"keywords": keywords, "content": content})


def unseed(apps, schema_editor):
    pass


class Migration(migrations.Migration):
    dependencies = [("assistant", "0001_initial")]
    operations = [migrations.RunPython(seed, unseed)]
