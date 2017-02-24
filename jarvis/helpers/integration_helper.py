from jarvis.helpers.configs import config


def oauth_url_for_integration(integration):
	if not integration or not integration.slug:
		return None
	
	slug = integration.slug
	
	if slug == 'uber':
		from uber_rides.auth import AuthorizationCodeGrant
		
		auth_flow = AuthorizationCodeGrant(
			config('UBER_CLIENT_ID'),
			set(config('UBER_SCOPES').split(',')),
			config('UBER_CLIENT_SECRET'),
			oauth_redirect_url(integration)
		)
		
		return auth_flow.get_authorization_url()


def oauth_redirect_url(integration):
	if integration and integration.slug:
		return '{}/oauth/{}'.format(config('URL').rstrip('/'), integration.slug)
	
	return None