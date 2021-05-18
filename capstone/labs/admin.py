from django.contrib import admin
from labs.models import Timeline


@admin.register(Timeline)
class TimelineAdmin(admin.ModelAdmin):

    def title(self, obj):
        return obj.timeline['title']

    def case_count(self, obj):
        if 'cases' in obj.timeline:
            return len(obj.timeline['cases'])
        return "🛑 no case list entry 😱"

    def event_count(self, obj):
        if 'events' in obj.timeline:
            return len(obj.timeline['events'])
        return "🛑 no events list entry 😱"

    list_display = ('id', 'uuid', 'created_by', 'title', 'case_count', 'event_count')

