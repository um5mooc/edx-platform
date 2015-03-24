define(['backbone', 'jquery', 'underscore', 'js/common_helpers/ajax_helpers', 'js/common_helpers/template_helpers',
        'js/spec/student_account/helpers',
        'js/student_account/views/account_settings_fields',
        'js/student_account/models/user_account_model',
        'js/student_account/models/user_preferences_model',
        'js/student_profile/learner_profile_view'
       ],
    function (Backbone, $, _, AjaxHelpers, TemplateHelpers, Helpers, FieldViews, UserAccountModel,
                AccountPreferencesModel, LearnerProfileView) {
        'use strict';

        describe("edx.user.LearnerProfileView", function (options) {

            var createLearnerProfileView = function (ownProfile) {

                var accountSettingsModel = new UserAccountModel();
                accountSettingsModel.set(Helpers.USER_ACCOUNTS_DATA);

                var accountPreferencesModel = new AccountPreferencesModel();
                accountPreferencesModel.url = Helpers.USER_PREFERENCES_API_URL;

                var editable = ownProfile ? 'toggle' : 'never';

                var accountPrivacyFieldView = new FieldViews.AccountPrivacyFieldView({
                    model: accountPreferencesModel,
                    required: true,
                    editable: 'always',
                    showMessages: false,
                    title: 'edX learners can see my:',
                    valueAttribute: "account_privacy",
                    options: [
                        ['private', 'Limited Profile'],
                        ['all_users', 'Full Profile']
                    ],
                    helpMessage: '',
                    accountSettingsPageUrl: '/account/settings/'
                });

                var usernameFieldView = new FieldViews.ReadonlyFieldView({
                        model: accountSettingsModel,
                        valueAttribute: "username",
                        helpMessage: ""
                });

                var sectionOneFieldViews = [
                    new FieldViews.DropdownFieldView({
                        model: accountSettingsModel,
                        required: false,
                        editable: editable,
                        showMessages: false,
                        iconName: 'fa-map-marker',
                        placeholderValue: 'Add country',
                        valueAttribute: "country",
                        options: Helpers.FIELD_OPTIONS,
                        helpMessage: ''
                    }),

                    new FieldViews.DropdownFieldView({
                        model: accountSettingsModel,
                        required: false,
                        editable: editable,
                        showMessages: false,
                        iconName: 'fa-comment fa-flip-horizontal',
                        placeholderValue: gettext('Add language'),
                        valueAttribute: "language",
                        options: options['language_options'],
                        helpMessage: ''
                    })
                ];

                var sectionTwoFieldViews = [
                    new FieldViews.TextareaFieldView({
                        model: accountSettingsModel,
                        editable: editable,
                        showMessages: false,
                        title: 'About me',
                        placeholderValue: "Tell other edX learners a little about yourself, where you're from, what your interests are, why you joined edX, what you hope to learn...",
                        valueAttribute: "bio",
                        helpMessage: ''
                    })
                ];

                var learnerProfileView = new LearnerProfileView(
                    {
                        el: $('.wrapper-profile'),
                        own_profile: ownProfile,
                        has_preferences_access: true,
                        accountSettingsModel: accountSettingsModel,
                        preferencesModel: accountPreferencesModel,
                        accountPrivacyFieldView: accountPrivacyFieldView,
                        usernameFieldView: usernameFieldView,
                        sectionOneFieldViews: sectionOneFieldViews,
                        sectionTwoFieldViews: sectionTwoFieldViews
                    });

                return learnerProfileView;
            };

            beforeEach(function () {
                setFixtures('<div class="wrapper-profile"></div>');
                TemplateHelpers.installTemplate('templates/fields/field_readonly');
                TemplateHelpers.installTemplate('templates/fields/field_dropdown');
                TemplateHelpers.installTemplate('templates/fields/field_textarea');
                TemplateHelpers.installTemplate('templates/student_profile/learner_profile');
            });


            var expectProfileSectionsButNotFieldsToBeRendered = function (learnerProfileView) {
                expectProfileSectionsAndFieldsToBeRendered(learnerProfileView, false)
            };

            var expectProfileSectionsAndFieldsToBeRendered = function (learnerProfileView, fieldsAreRendered) {
                var accountPrivacyElement = learnerProfileView.$('.wrapper-profile-field-account-privacy');

                var privacyFieldElement  = $(accountPrivacyElement).find('u-field');
                if (fieldsAreRendered === false) {
                    expect(privacyFieldElement.length).toBe(0);
                } else {
                    expect(privacyFieldElement.length).toBe(1);

                    var fieldTitle = $(privacyFieldElement).find('.u-field-title').text().trim(),
                        view = learnerProfileView.options.accountPrivacyFieldView;

                    expect(fieldTitle).toBe(view.options.title);

                    if ('fieldValue' in view) {
                        expect(view.model.get(view.options.valueAttribute)).toBeTruthy();
                        expect(view.fieldValue()).toBe(view.modelValue());
                    }
                }

                var sectionElements = learnerProfileView.$('.section');
                var sectionsData = learnerProfileView.options.sectionsData;

                _.each(sectionElements, function(sectionElement, sectionIndex) {
                    expect($(sectionElement).find('.section-header').text().trim()).toBe(sectionsData[sectionIndex].title);

                    var sectionFieldElements = $(sectionElement).find('.u-field');

                    if (fieldsAreRendered === false) {
                        expect(sectionFieldElements.length).toBe(0);
                    } else {
                        expect(sectionFieldElements.length).toBe(sectionsData[sectionIndex].fields.length);

                        _.each(sectionFieldElements, function (sectionFieldElement, fieldIndex) {
                            expectElementContainsField(sectionFieldElement, sectionsData[sectionIndex].fields[fieldIndex]);
                        });
                    }
                });
            };

            it("shows loading error correctly", function() {

                var learnerProfileView = createLearnerProfileView();

                learnerProfileView.render();
                Helpers.expectLoadingIndicatorIsVisible(learnerProfileView, true);
                Helpers.expectLoadingErrorIsVisible(learnerProfileView, false);
                expectProfileSectionsButNotFieldsToBeRendered(learnerProfileView);

                learnerProfileView.showLoadingError();
                Helpers.expectLoadingIndicatorIsVisible(learnerProfileView, false);
                Helpers.expectLoadingErrorIsVisible(learnerProfileView, true);
                expectProfileSectionsButNotFieldsToBeRendered(learnerProfileView);
            });

            it("renders all fields as expected", function() {

                var accountSettingsView = createLearnerProfileView();

                accountSettingsView.render();
                Helpers.expectLoadingIndicatorIsVisible(accountSettingsView, true);
                Helpers.expectLoadingErrorIsVisible(accountSettingsView, false);
                expectProfileSectionsButNotFieldsToBeRendered(accountSettingsView);

                accountSettingsView.renderFields();
                Helpers.expectLoadingIndicatorIsVisible(accountSettingsView, false);
                Helpers.expectLoadingErrorIsVisible(accountSettingsView, false);
                expectProfileSectionsAndFieldsToBeRendered(accountSettingsView)
            });

        });
    });
