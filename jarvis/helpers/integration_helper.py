from jarvis.helpers.configs import config
import db_helper as db
from models import Integration


def oauth_url_for_integration(integration, user=None):
	if not integration or not integration.slug:
		return None
	
	slug = integration.slug
	
	if user:
		state = user.uid
	else:
		state = None
	
	if slug == 'uber':
		auth_flow = uber_auth_flow(state, integration)
		return auth_flow.get_authorization_url()


def oauth_redirect_url(integration):
	if integration and integration.slug:
		return '{}/oauth/{}'.format(config('URL').rstrip('/'), integration.slug)
	
	return None


def uber_auth_flow(state_token=None, integration=None):
	from uber_rides.auth import AuthorizationCodeGrant
	
	if not integration:
		integration = db.find(Integration, {'slug': 'uber'})
	
	return AuthorizationCodeGrant(
		client_id=config('UBER_CLIENT_ID'),
		scopes=set(config('UBER_SCOPES').split(',')),
		client_secret=config('UBER_CLIENT_SECRET'),
		redirect_url=oauth_redirect_url(integration),
		state_token=state_token
	)