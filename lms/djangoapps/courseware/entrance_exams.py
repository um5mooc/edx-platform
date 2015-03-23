"""
This file contains (or should), all entrance exam related utils/logic.
"""
from django.conf import settings

from courseware.access import has_access
from courseware.model_data import FieldDataCache
from courseware.models import StudentModule
from opaque_keys.edx.keys import UsageKey
from student.models import EntranceExamConfiguration
from util.milestones_helpers import get_required_content
from util.module_utils import yield_dynamic_descriptor_descendents
from xmodule.modulestore.django import modulestore


def feature_is_enabled():
    """
    Checks to see if the Entrance Exams feature is enabled
    Use this operation instead of checking the feature flag all over the place
    """
    return settings.FEATURES.get('ENTRANCE_EXAMS', False)


def course_has_entrance_exam(course):
    """
    Checks to see if a course is properly configured for an entrance exam
    """
    if not feature_is_enabled():
        return False
    if not course.entrance_exam_enabled:
        return False
    if not course.entrance_exam_id:
        return False
    return True


def user_can_skip_entrance_exam(request, user, course):
    """
    Checks all of the various override conditions for a user to skip an entrance exam
    """
    if not course_has_entrance_exam(course):
        return True
    if user.is_anonymous():
        return False
    if has_access(user, 'staff', course):
        return True
    if EntranceExamConfiguration.user_can_skip_entrance_exam(user, course.id):
        return True
    exam_content = get_entrance_exam_content(request, course)
    if not exam_content:
        return True
    return False


def user_has_passed_entrance_exam(request, user, course):
    """
    Checks to see if the user has attained a sufficient score to pass the exam
    """
    if not course_has_entrance_exam(course):
        return True
    if user.is_anonymous():
        return False
    entrance_exam_score = get_entrance_exam_score(request, course)
    if entrance_exam_score >= course.entrance_exam_minimum_score_pct:
        return True
    return False


# pylint: disable=invalid-name
def user_can_access_courseware_with_entrance_exam(request, user, course):
    """
    Checks all of the various access/override workflows to see if the user
    is allowed to access the course content, or if they have to view the exam
    """
    if not course_has_entrance_exam(course):
        return True
    if user_can_skip_entrance_exam(request, user, course):
        return True
    if user_has_passed_entrance_exam(request, user, course):
        return True
    return False


def _calculate_entrance_exam_score(user, course_descriptor, exam_modules):
    """
    Calculates the score (percent) of the entrance exam using the provided modules
    """
    # All of the exam module ids
    exam_module_ids = [exam_module.location for exam_module in exam_modules]

    # All of the corresponding student module records
    student_modules = StudentModule.objects.filter(
        student=user,
        course_id=course_descriptor.id,
        module_state_key__in=exam_module_ids,
    )
    exam_pct = 0
    module_pcts = []
    ignore_categories = ['course', 'chapter', 'sequential', 'vertical']

    for module in exam_modules:
        if module.graded and module.category not in ignore_categories:
            module_pct = 0
            for student_module in student_modules:
                if unicode(student_module.module_state_key) == unicode(module.location) and student_module.max_grade:
                    module_pct = student_module.grade / student_module.max_grade
                    break
            module_pcts.append(module_pct)
    if module_pcts:
        exam_pct = sum(module_pcts) / float(len(module_pcts))
    return exam_pct


def get_entrance_exam_score(request, course):
    """
    Get entrance exam score
    """
    exam_key = UsageKey.from_string(course.entrance_exam_id)
    exam_descriptor = modulestore().get_item(exam_key)

    def inner_get_module(descriptor):
        """
        Delegate to get_module_for_descriptor (imported here to avoid circular reference)
        """
        from courseware.module_render import get_module_for_descriptor
        field_data_cache = FieldDataCache([descriptor], course.id, request.user)
        return get_module_for_descriptor(
            request.user,
            request,
            descriptor,
            field_data_cache,
            course.id
        )

    exam_module_generators = yield_dynamic_descriptor_descendents(
        exam_descriptor,
        inner_get_module
    )
    exam_modules = [module for module in exam_module_generators]
    return _calculate_entrance_exam_score(request.user, course, exam_modules)


def get_entrance_exam_content(request, course):
    """
    Get the entrance exam content information e.g. chapter, exam passing state.
    return exam chapter and its passing state.
    """
    required_content = get_required_content(course, request.user)

    exam_module = None
    for content in required_content:
        usage_key = course.id.make_usage_key_from_deprecated_string(content)
        module_item = modulestore().get_item(usage_key)
        if not module_item.hide_from_toc and module_item.is_entrance_exam:
            exam_module = module_item
            break
    return exam_module
