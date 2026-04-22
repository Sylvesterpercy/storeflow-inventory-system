from .models import UserProfile


# this automatically passes org to every template
def org_context(request):
    org = None
    if request.user.is_authenticated:
        try:
            profile = UserProfile.objects.get(user=request.user)
            org = profile.organization
        except UserProfile.DoesNotExist:
            pass
    return {'org': org}
