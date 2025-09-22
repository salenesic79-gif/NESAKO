from django.db import models

class MemoryEntry(models.Model):
    key = models.CharField(max_length=255, unique=True)
    value = models.TextField()
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"MemoryEntry(key={self.key})"

class Conversation(models.Model):
    user_input = models.TextField()
    assistant_response = models.TextField()
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"Conversation(id={self.id}, created_at={self.created_at})"

class LearningData(models.Model):
    pattern = models.TextField(unique=True)
    response = models.TextField()
    usage_count = models.IntegerField(default=0)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"LearningData(id={self.id}, pattern={self.pattern[:30]}...)"

class LessonLearned(models.Model):
    lesson_text = models.TextField()
    source = models.CharField(max_length=255, blank=True, null=True)
    user = models.CharField(max_length=255, blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)
    feedback = models.CharField(max_length=10, default="pending")  # correct/incorrect/pending

    def __str__(self):
        return f"LessonLearned(id={self.id}, feedback={self.feedback})"
