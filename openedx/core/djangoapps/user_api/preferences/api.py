"""
API for managing user preferences.
"""
import datetime
import logging
import string
import analytics
from eventtracking import tracker
from pytz import UTC

from django.conf import settings
from django.contrib.auth.models import User
from django.core.exceptions import ObjectDoesNotExist
from django.db import transaction, IntegrityError
from django.utils.translation import ugettext as _

from student.models import UserProfile

from ..errors import (
    UserAPIInternalError, UserAPIRequestError, UserNotFound, UserNotAuthorized,
    PreferenceValidationError, PreferenceUpdateError
)
from ..helpers import intercept_errors
from ..models import UserOrgTag, UserPreference
from ..serializers import UserSerializer, RawUserPreferenceSerializer

log = logging.getLogger(__name__)


@intercept_errors(UserAPIInternalError, ignore_errors=[UserAPIRequestError])
def get_user_preference(requesting_user, preference_key, username=None):
    """Returns the value of the user preference with the specified key.

    Args:
        requesting_user (User): The user requesting the user preferences. Only the user with username
            `username` or users with "is_staff" privileges can access the preferences.
        preference_key (string): The key for the user preference.
        username (str): Optional username for which to look up the preferences. If not specified,
            `requesting_user.username` is assumed.

    Returns:
         The value for the user preference which is always a string, or None if a preference
         has not been specified.

    Raises:
         UserNotFound: no user with username `username` exists (or `requesting_user.username` if
            `username` is not specified)
         UserNotAuthorized: the requesting_user does not have access to the user preference.
         UserAPIInternalError: the operation failed due to an unexpected error.
    """
    existing_user = _get_user(requesting_user, username, allow_staff=True)
    return UserPreference.get_value(existing_user, preference_key)


@intercept_errors(UserAPIInternalError, ignore_errors=[UserAPIRequestError])
def get_user_preferences(requesting_user, username=None):
    """Returns all user preferences as a JSON response.

    Args:
        requesting_user (User): The user requesting the user preferences. Only the user with username
            `username` or users with "is_staff" privileges can access the preferences.
        username (str): Optional username for which to look up the preferences. If not specified,
            `requesting_user.username` is assumed.

    Returns:
         A dict containing account fields.

    Raises:
         UserNotFound: no user with username `username` exists (or `requesting_user.username` if
            `username` is not specified)
         UserNotAuthorized: the requesting_user does not have access to the user preference.
         UserAPIInternalError: the operation failed due to an unexpected error.
    """
    existing_user = _get_user(requesting_user, username, allow_staff=True)
    user_serializer = UserSerializer(existing_user)
    return user_serializer.data["preferences"]


@intercept_errors(UserAPIInternalError, ignore_errors=[UserAPIRequestError])
@transaction.commit_on_success
def update_user_preferences(requesting_user, update, username=None):
    """Update the user preferences for the given username.

    Note:
        It is up to the caller of this method to enforce the contract that this method is only called
        with the user who made the request.

    Arguments:
        requesting_user (User): The user requesting to modify account information. Only the user with username
            'username' has permissions to modify account information.
        update (dict): The updated account field values.
            Some notes:
                Values are expected to be strings. Non-string values will be converted to strings.
                Null values for a preference will be treated as a request to delete the key in question.
        username (string): Optional username specifying which account should be updated. If not specified,
            `requesting_user.username` is assumed.

    Raises:
        UserNotFound: no user with username `username` exists (or `requesting_user.username` if
            `username` is not specified)
        UserNotAuthorized: the requesting_user does not have access to change the account
            associated with `username`
        PreferenceValidationError: the update was not attempted because validation errors were found
        PreferenceUpdateError: the operation failed when performing the update.
        UserAPIInternalError: the operation failed due to an unexpected error.
    """
    existing_user = _get_user(requesting_user, username)

    # First validate each preference setting
    errors = {}
    serializers = {}
    for preference_key in update.keys():
        preference_value = update[preference_key]
        if preference_value is not None:
            try:
                serializer = create_user_preference_serializer(existing_user, preference_key, preference_value)
                validate_user_preference_serializer(serializer, preference_key, preference_value)
                serializers[preference_key] = serializer
            except PreferenceValidationError as error:
                preference_error = error.preference_errors[preference_key]
                errors[preference_key] = {
                    "developer_message": preference_error["developer_message"],
                    "user_message": preference_error["user_message"],
                }
    if errors:
        raise PreferenceValidationError(errors)
    # Then perform the patch
    for preference_key in update.keys():
        preference_value = update[preference_key]
        if preference_value is not None:
            try:
                serializer = serializers[preference_key]
                serializer.save()
            except Exception as error:
                raise _create_preference_update_error(preference_key, preference_value, error)
        else:
            delete_user_preference(requesting_user, preference_key)


@intercept_errors(UserAPIInternalError, ignore_errors=[UserAPIRequestError])
@transaction.commit_on_success
def set_user_preference(requesting_user, preference_key, preference_value, username=None):
    """Update a user preference for the given username.

    Note:
        It is up to the caller of this method to enforce the contract that this method is only called
        with the user who made the request.

    Arguments:
        requesting_user (User): The user requesting to modify account information. Only the user with username
            'username' has permissions to modify account information.
        preference_key (string): The key for the user preference.
        preference_value (string): The value to be stored. Non-string values will be converted to strings.
        username (string): Optional username specifying which account should be updated. If not specified,
            `requesting_user.username` is assumed.

    Raises:
        UserNotFound: no user with username `username` exists (or `requesting_user.username` if
            `username` is not specified)
        UserNotAuthorized: the requesting_user does not have access to change the account
            associated with `username`
        PreferenceValidationError: the update was not attempted because validation errors were found
        PreferenceUpdateError: the operation failed when performing the update.
        UserAPIInternalError: the operation failed due to an unexpected error.
    """
    existing_user = _get_user(requesting_user, username)
    serializer = create_user_preference_serializer(existing_user, preference_key, preference_value)
    validate_user_preference_serializer(serializer, preference_key, preference_value)
    try:
        serializer.save()
    except Exception as error:
        raise _create_preference_update_error(preference_key, preference_value, error)


@intercept_errors(UserAPIInternalError, ignore_errors=[UserAPIRequestError])
@transaction.commit_on_success
def delete_user_preference(requesting_user, preference_key, username=None):
    """Deletes a user preference on behalf of a requesting user.

    Note:
        It is up to the caller of this method to enforce the contract that this method is only called
        with the user who made the request.

    Arguments:
        requesting_user (User): The user requesting to delete the preference. Only the user with username
            'username' has permissions to delete their own preference.
        preference_key (string): The key for the user preference.
        username (string): Optional username specifying which account should be updated. If not specified,
            `requesting_user.username` is assumed.

    Returns:
        True if the preference was deleted, False if the user did not have a preference with the supplied key.

    Raises:
        UserNotFound: no user with username `username` exists (or `requesting_user.username` if
            `username` is not specified)
        UserNotAuthorized: the requesting_user does not have access to change the account
            associated with `username`
        PreferenceUpdateError: the operation failed when performing the update.
        UserAPIInternalError: the operation failed due to an unexpected error.
    """
    existing_user = _get_user(requesting_user, username)
    try:
        user_preference = UserPreference.objects.get(user=existing_user, key=preference_key)
    except ObjectDoesNotExist:
        return False

    try:
        user_preference.delete()
    except Exception as error:
        raise PreferenceUpdateError(
            developer_message=u"Delete failed for user preference '{preference_key}': {error}".format(
                preference_key=preference_key, error=error
            ),
            user_message=_(u"Delete failed for user preference '{preference_key}'.").format(
                preference_key=preference_key
            ),
        )
    return True


@intercept_errors(UserAPIInternalError, ignore_errors=[UserAPIRequestError])
def update_email_opt_in(user, org, optin):
    """Updates a user's preference for receiving org-wide emails.

    Sets a User Org Tag defining the choice to opt in or opt out of organization-wide
    emails.

    Arguments:
        user (User): The user to set a preference for.
        org (str): The org is used to determine the organization this setting is related to.
        optin (Boolean): True if the user is choosing to receive emails for this organization. If the user is not
            the correct age to receive emails, email-optin is set to False regardless.

    Returns:
        None

    """
    # Avoid calling get_account_settings because it introduces circularity for many callers who need both
    # preferences and account information.
    try:
        user_profile = UserProfile.objects.get(user=user)
    except ObjectDoesNotExist:
        raise UserNotFound()

    year_of_birth = user_profile.year_of_birth
    of_age = (
        year_of_birth is None or  # If year of birth is not set, we assume user is of age.
        datetime.datetime.now(UTC).year - year_of_birth >  # pylint: disable=maybe-no-member
        getattr(settings, 'EMAIL_OPTIN_MINIMUM_AGE', 13)
    )

    try:
        preference, _ = UserOrgTag.objects.get_or_create(
            user=user, org=org, key='email-optin'
        )
        preference.value = str(optin and of_age)
        preference.save()

        if settings.FEATURES.get('SEGMENT_IO_LMS') and settings.SEGMENT_IO_LMS_KEY:
            _track_update_email_opt_in(user.id, org, optin)

    except IntegrityError as err:
        log.warn(u"Could not update organization wide preference due to IntegrityError: {}".format(err.message))


def _track_update_email_opt_in(user_id, organization, opt_in):
    """Track an email opt-in preference change.

    Arguments:
        user_id (str): The ID of the user making the preference change.
        organization (str): The organization whose emails are being opted into or out of by the user.
        opt_in (Boolean): Whether the user has chosen to opt-in to emails from the organization.

    Returns:
        None

    """
    event_name = 'edx.bi.user.org_email.opted_in' if opt_in else 'edx.bi.user.org_email.opted_out'
    tracking_context = tracker.get_tracker().resolve_context()

    analytics.track(
        user_id,
        event_name,
        {
            'category': 'communication',
            'label': organization
        },
        context={
            'Google Analytics': {
                'clientId': tracking_context.get('client_id')
            }
        }
    )


def _get_user(requesting_user, username=None, allow_staff=False):
    """
    Helper method to return the user for a given username.
    If username is not provided, requesting_user.username is assumed.
    """
    if username is None:
        username = requesting_user.username

    try:
        existing_user = User.objects.get(username=username)
    except ObjectDoesNotExist:
        raise UserNotFound()

    if requesting_user.username != username:
        if not requesting_user.is_staff or not allow_staff:
            raise UserNotAuthorized()

    return existing_user


def create_user_preference_serializer(user, preference_key, preference_value):
    """Creates a serializer for the specified user preference.

    Arguments:
        user (User): The user whose preference is being serialized.
        preference_key (string): The key for the user preference.
        preference_value (string): The value to be stored. Non-string values will be converted to strings.

    Returns:
        A serializer that can be used to save the user preference.
    """
    try:
        existing_user_preference = UserPreference.objects.get(user=user, key=preference_key)
    except ObjectDoesNotExist:
        existing_user_preference = None
    new_data = {
        "user": user.id,
        "key": preference_key,
        "value": preference_value,
    }
    if existing_user_preference:
        serializer = RawUserPreferenceSerializer(existing_user_preference, data=new_data)
    else:
        serializer = RawUserPreferenceSerializer(data=new_data)
    return serializer


def validate_user_preference_serializer(serializer, preference_key, preference_value):
    """Validates a user preference serializer.

    Arguments:
        serializer (UserPreferenceSerializer): The serializer to be validated.
        preference_key (string): The key for the user preference.
        preference_value (string): The value to be stored. Non-string values will be converted to strings.

    Raises:
        PreferenceValidationError: the supplied key and/or value for a user preference are invalid.
    """
    if preference_value is None or unicode(preference_value).strip() == '':
        message = _(u"Preference '{preference_key}' cannot be set to an empty value.").format(
            preference_key=preference_key
        )
        raise PreferenceValidationError({
            preference_key: {"developer_message": message, "user_message": message}
        })
    if not serializer.is_valid():
        developer_message = u"Value '{preference_value}' not valid for preference '{preference_key}': {error}".format(
            preference_key=preference_key, preference_value=preference_value, error=serializer.errors
        )
        if serializer.errors["key"]:
            user_message = _(u"Invalid user preference key '{preference_key}'.").format(
                preference_key=preference_key
            )
        else:
            user_message = _(u"Value '{preference_value}' is not valid for user preference '{preference_key}'.").format(
                preference_key=preference_key, preference_value=preference_value
            )
        raise PreferenceValidationError({
            preference_key: {
                "developer_message": developer_message,
                "user_message": user_message,
            }
        })


def _create_preference_update_error(preference_key, preference_value, error):
    """ Creates a PreferenceUpdateError with developer_message and user_message. """
    return PreferenceUpdateError(
        developer_message=u"Save failed for user preference '{key}' with value '{value}': {error}".format(
            key=preference_key, value=preference_value, error=error
        ),
        user_message=_(u"Save failed for user preference '{key}' with value '{value}'.").format(
            key=preference_key, value=preference_value
        ),
    )
