from django.contrib import admin
from .models import Conversation, MemoryEntry, LearningData, LessonLearned

@admin.register(Conversation)
class ConversationAdmin(admin.ModelAdmin):
    list_display = ("id", "created_at", "short_user_input", "short_assistant_response")
    list_filter = ("created_at",)
    search_fields = ("user_input", "assistant_response")
    ordering = ("-created_at",)

    def short_user_input(self, obj):
        return (obj.user_input or "")[:80]
    short_user_input.short_description = "User input"

    def short_assistant_response(self, obj):
        return (obj.assistant_response or "")[:80]
    short_assistant_response.short_description = "Assistant response"

@admin.register(MemoryEntry)
class MemoryEntryAdmin(admin.ModelAdmin):
    list_display = ("id", "key", "created_at", "updated_at", "short_value")
    search_fields = ("key", "value")
    ordering = ("-updated_at",)

    def short_value(self, obj):
        v = obj.value or ""
        return v[:100]
    short_value.short_description = "Value"

@admin.register(LearningData)
class LearningDataAdmin(admin.ModelAdmin):
    list_display = ("id", "pattern_short", "usage_count", "created_at")
    search_fields = ("pattern", "response")
    ordering = ("-created_at",)

    def pattern_short(self, obj):
        return (obj.pattern or "")[:80]
    pattern_short.short_description = "Pattern"

@admin.register(LessonLearned)
class LessonLearnedAdmin(admin.ModelAdmin):
    list_display = ("id", "feedback", "user", "source", "created_at", "lesson_short")
    list_filter = ("feedback", "created_at")
    search_fields = ("lesson_text", "user", "source")
    ordering = ("-created_at",)

    def lesson_short(self, obj):
        return (obj.lesson_text or "")[:100]
    lesson_short.short_description = "Lesson"
