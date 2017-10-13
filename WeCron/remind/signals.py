from django.dispatch import Signal

participant_modified = Signal(providing_args=['participant', 'add'])