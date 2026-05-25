def save_profile(backend, user, response, *args, **kwargs):
    if backend.name == 'google-oauth2':
        if not user.first_name:
            user.first_name = response.get('given_name', '')
        if not user.last_name:
            user.last_name = response.get('family_name', '')
        if not user.is_email_verified:
            user.is_email_verified = True
        user.save(update_fields=['first_name', 'last_name', 'is_email_verified'])
    elif backend.name == 'facebook':
        if not user.first_name:
            user.first_name = response.get('first_name', '')
        if not user.last_name:
            user.last_name = response.get('last_name', '')
        user.save(update_fields=['first_name', 'last_name'])
