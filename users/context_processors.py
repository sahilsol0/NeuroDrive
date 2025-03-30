# users/context_processors.py
from .models import Ride

def active_ride_context(request):
    active_ride_id = None
    if request.user.is_authenticated and not request.user.is_driver:
        # Find the passenger's active ride (assigned or in_progress)
        active_ride = Ride.objects.filter(
            passenger=request.user,
            status__in=['assigned', 'in_progress']
        ).select_related(None).only('id').first() # Optimize query
        if active_ride:
            active_ride_id = active_ride.id
    return {'active_ride_id': active_ride_id}