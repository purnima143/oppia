# Copyright 2014 The Oppia Authors. All Rights Reserved.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#      http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS-IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

"""Controllers for the profile page."""

from core.controllers import base
from core.domain import email_manager
from core.domain import summary_services
from core.domain import user_services
import feconf
import utils


def require_user_id_else_redirect_to_homepage(handler):
    """Decorator that checks if a user_id is associated to the current
    session. If not, the user is redirected to the main page.

    Note that the user may not yet have registered.
    """
    def test_login(self, **kwargs):
        """Checks if the user for the current session is logged in.

        If not, redirects the user to the home page.
        """
        if not self.user_id:
            self.redirect('/')
            return
        return handler(self, **kwargs)

    return test_login


class ProfilePage(base.BaseHandler):
    """The world-viewable profile page."""

    PAGE_NAME_FOR_CSRF = 'profile'

    def get(self, username):
        """Handles GET requests for the publicly-viewable profile page."""
        if not username:
            raise self.PageNotFoundException

        user_settings = user_services.get_user_settings_from_username(username)

        if not user_settings:
            raise self.PageNotFoundException

        self.values.update({
            'nav_mode': feconf.NAV_MODE_PROFILE,
            'PROFILE_USERNAME': username,
        })
        self.render_template('profile/profile.html')


class ProfileHandler(base.BaseHandler):
    """Provides data for the profile page."""

    PAGE_NAME_FOR_CSRF = 'profile'

    def get(self, username):
        """Handles GET requests."""
        if not username:
            raise self.PageNotFoundException

        user_settings = user_services.get_user_settings_from_username(username)
        if not user_settings:
            raise self.PageNotFoundException

        created_exp_summary_dicts = []
        edited_exp_summary_dicts = []

        user_contributions = user_services.get_user_contributions(
            user_settings.user_id)
        if user_contributions:
            created_exp_summary_dicts = (
                summary_services.get_displayable_exp_summary_dicts_matching_ids(
                    user_contributions.created_exploration_ids))
            edited_exp_summary_dicts = (
                summary_services.get_displayable_exp_summary_dicts_matching_ids(
                    user_contributions.edited_exploration_ids))

        self.values.update({
            'user_bio': user_settings.user_bio,
            'subject_interests': user_settings.subject_interests,
            'first_contribution_msec': (
                user_settings.first_contribution_msec
                if user_settings.first_contribution_msec else None),
            'profile_picture_data_url': user_settings.profile_picture_data_url,
            'user_impact_score':user_services.get_user_impact_score(
                user_settings.user_id),
            'created_exp_summary_dicts': created_exp_summary_dicts,
            'edited_exp_summary_dicts': edited_exp_summary_dicts,
        })
        self.render_json(self.values)


class PreferencesPage(base.BaseHandler):
    """The preferences page."""

    PAGE_NAME_FOR_CSRF = 'preferences'

    @base.require_user
    def get(self):
        """Handles GET requests."""
        self.values.update({
            'nav_mode': feconf.NAV_MODE_PROFILE,
            'LANGUAGE_CODES_AND_NAMES': (
                utils.get_all_language_codes_and_names()),
        })
        self.render_template(
            'profile/preferences.html', redirect_url_on_logout='/')


class PreferencesHandler(base.BaseHandler):
    """Provides data for the preferences page."""

    PAGE_NAME_FOR_CSRF = 'preferences'

    @base.require_user
    def get(self):
        """Handles GET requests."""
        user_settings = user_services.get_user_settings(self.user_id)
        user_services.generate_profile_picture(self.user_id)
        self.values.update({
            'preferred_language_codes': user_settings.preferred_language_codes,
            'profile_picture_data_url': user_settings.profile_picture_data_url,
            'user_bio': user_settings.user_bio,
            'subject_interests': user_settings.subject_interests,
            'can_receive_email_updates': user_services.get_email_preferences(
                self.user_id)['can_receive_email_updates'],
        })
        self.render_json(self.values)

    @base.require_user
    def put(self):
        """Handles POST requests."""
        update_type = self.payload.get('update_type')
        data = self.payload.get('data')

        if update_type == 'user_bio':
            user_services.update_user_bio(self.user_id, data)
        elif update_type == 'subject_interests':
            user_services.update_subject_interests(self.user_id, data)
        elif update_type == 'preferred_language_codes':
            user_services.update_preferred_language_codes(self.user_id, data)
        elif update_type == 'profile_picture_data_url':
            user_services.update_profile_picture_data_url(self.user_id, data)
        elif update_type == 'can_receive_email_updates':
            user_services.update_email_preferences(self.user_id, data)
        else:
            raise self.InvalidInputException(
                'Invalid update type: %s' % update_type)

        self.render_json({})


class ProfilePictureHandler(base.BaseHandler):
    """Provides the dataURI of the user's profile picture, or none if no user
    picture is uploaded."""

    @base.require_user
    def get(self):
        """Handles GET requests."""
        user_settings = user_services.get_user_settings(self.user_id)
        self.values.update({
            'profile_picture_data_url': user_settings.profile_picture_data_url
        })
        self.render_json(self.values)


class ProfilePictureHandlerByUsername(base.BaseHandler):
    """ Provides the dataURI of the profile picture of the specified user,
    or None if no user picture is uploaded for the user with that ID."""
    def get(self, username):
        user_id = user_services.get_user_id_from_username(username)
        if user_id is None:
            raise self.PageNotFoundException

        user_settings = user_services.get_user_settings(user_id)
        self.values.update({
            'profile_picture_data_url_for_username': (
                user_settings.profile_picture_data_url)
        })
        self.render_json(self.values)


class SignupPage(base.BaseHandler):
    """The page which prompts for username and acceptance of terms."""

    PAGE_NAME_FOR_CSRF = 'signup'
    REDIRECT_UNFINISHED_SIGNUPS = False

    @require_user_id_else_redirect_to_homepage
    def get(self):
        """Handles GET requests."""
        return_url = str(self.request.get('return_url', self.request.uri))

        if user_services.has_fully_registered(self.user_id):
            self.redirect(return_url)
            return

        self.values.update({
            'nav_mode': feconf.NAV_MODE_SIGNUP,
            'CAN_SEND_EMAILS_TO_USERS': feconf.CAN_SEND_EMAILS_TO_USERS,
        })
        self.render_template('profile/signup.html')


class SignupHandler(base.BaseHandler):
    """Provides data for the editor prerequisites page."""

    PAGE_NAME_FOR_CSRF = 'signup'
    REDIRECT_UNFINISHED_SIGNUPS = False

    @require_user_id_else_redirect_to_homepage
    def get(self):
        """Handles GET requests."""
        user_settings = user_services.get_user_settings(self.user_id)
        self.render_json({
            'has_agreed_to_latest_terms': (
                user_settings.last_agreed_to_terms and
                user_settings.last_agreed_to_terms >=
                feconf.REGISTRATION_PAGE_LAST_UPDATED_UTC),
            'has_ever_registered': bool(
                user_settings.username and user_settings.last_agreed_to_terms),
            'username': user_settings.username,
        })

    @require_user_id_else_redirect_to_homepage
    def post(self):
        """Handles POST requests."""
        username = self.payload.get('username')
        agreed_to_terms = self.payload.get('agreed_to_terms')
        can_receive_email_updates = self.payload.get(
            'can_receive_email_updates')

        has_ever_registered = user_services.has_ever_registered(self.user_id)
        has_fully_registered = user_services.has_fully_registered(self.user_id)

        if has_fully_registered:
            self.render_json({})
            return

        if not isinstance(agreed_to_terms, bool) or not agreed_to_terms:
            raise self.InvalidInputException(
                'In order to edit explorations on this site, you will '
                'need to accept the license terms.')
        else:
            user_services.record_agreement_to_terms(self.user_id)

        if not user_services.get_username(self.user_id):
            try:
                user_services.set_username(self.user_id, username)
            except utils.ValidationError as e:
                raise self.InvalidInputException(e)

        if can_receive_email_updates is not None:
            user_services.update_email_preferences(
                self.user_id, can_receive_email_updates)

        # Note that an email is only sent when the user registers for the first
        # time.
        if feconf.CAN_SEND_EMAILS_TO_USERS and not has_ever_registered:
            email_manager.send_post_signup_email(self.user_id)

        user_services.generate_profile_picture(self.user_id)

        self.render_json({})


class UsernameCheckHandler(base.BaseHandler):
    """Checks whether a username has already been taken."""

    PAGE_NAME_FOR_CSRF = 'signup'
    REDIRECT_UNFINISHED_SIGNUPS = False

    @require_user_id_else_redirect_to_homepage
    def post(self):
        """Handles POST requests."""
        username = self.payload.get('username')
        try:
            user_services.UserSettings.require_valid_username(username)
        except utils.ValidationError as e:
            raise self.InvalidInputException(e)

        username_is_taken = user_services.is_username_taken(username)
        self.render_json({
            'username_is_taken': username_is_taken,
        })
