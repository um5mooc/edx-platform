"""
This file contains (or should), all entrance exam related utils/logic.
"""
from django.conf import settings

from opaque_keys.edx.keys import UsageKey
from xmodule.modulestore.django import modulestore
from student.models import EntranceExamConfiguration
from courseware.models import StudentModule
from courseware.access import has_access
from courseware.model_data import FieldDataCache
from util.module_utils import yield_dynamic_descriptor_descendents
from util.milestones_helpers import (
    serialize_user,
    get_course_milestones_fulfillment_paths,
)

from milestones.exceptions import InvalidMilestoneRelationshipTypeException


def can_skip_entrance_exam(user, course):
    """
    Returns True if user is allowed to skip entrance exam
    for the given course otherwise return False.
    In case of anonymous user returns False also.
    """
    if settings.FEATURES.get('ENTRANCE_EXAMS') and getattr(course, 'entrance_exam_enabled', False):
        if user.is_anonymous():
            return False

        if EntranceExamConfiguration.user_can_skip_entrance_exam(user, course.id) or has_access(user, 'staff', course):
            return True
        else:
            return False
    else:
        return True


def has_passed_entrance_exam(user, course):
    """
    Returns True if user has passed entrance exam
    for the given course otherwise returns False.
    In case of anonymous user returns False also.
    """
    if settings.FEATURES.get('ENTRANCE_EXAMS') and getattr(course, 'entrance_exam_enabled', False):
        if user.is_anonymous():
            return False

        if get_required_content(course, user):
            return False
        else:
            return True
    else:
        return True


def can_view_courseware_with_entrance_exam(user, course):
    """
    Returns True if user is allowed to access courseware for a course
    where entrance exam is enabled otherwise return False.
    """
    if can_skip_entrance_exam(user, course) or has_passed_entrance_exam(user, course):
        return True
    else:
        return False


def calculate_entrance_exam_score(user, course_descriptor, exam_modules):
    """
    Calculates the score (percent) of the entrance exam using the provided modules
    """
    exam_module_ids = [exam_module.location for exam_module in exam_modules]
    student_modules = StudentModule.objects.filter(
        student=user,
        course_id=course_descriptor.id,
        module_state_key__in=exam_module_ids,
    )
    exam_pct = 0
    if student_modules:
        module_pcts = []
        ignore_categories = ['course', 'chapter', 'sequential', 'vertical']
        for module in exam_modules:
            if module.graded and module.category not in ignore_categories:
                module_pct = 0
                try:
                    student_module = student_modules.get(module_state_key=module.location)
                    if student_module.max_grade:
                        module_pct = student_module.grade / student_module.max_grade
                    module_pcts.append(module_pct)
                except StudentModule.DoesNotExist:
                    pass
        if module_pcts:
            exam_pct = sum(module_pcts) / float(len(module_pcts))
    return exam_pct


def get_entrance_exam_score(request, course):
    """
    Get entrance exam score
    """
    from courseware.module_render import get_module_for_descriptor
    exam_key = UsageKey.from_string(course.entrance_exam_id)
    exam_descriptor = modulestore().get_item(exam_key)

    def inner_get_module(descriptor):
        """
        Delegate to get_module_for_descriptor.
        """
        field_data_cache = FieldDataCache([descriptor], course.id, request.user)
        return get_module_for_descriptor(request.user, request, descriptor, field_data_cache, course.id)

    exam_module_generators = yield_dynamic_descriptor_descendents(
        exam_descriptor,
        inner_get_module
    )
    exam_modules = [module for module in exam_module_generators]
    return calculate_entrance_exam_score(request.user, course, exam_modules)


def get_entrance_exam_content_info(request, course):
    """
    Get the entrance exam content information e.g. chapter, exam passing state.
    return exam chapter and its passing state.
    """
    required_content = get_required_content(course, request.user)
    exam_chapter = None
    is_exam_passed = True
    # Iterating the list of required content of this course.
    for content in required_content:
        # database lookup to required content pointer
        usage_key = course.id.make_usage_key_from_deprecated_string(content)
        module_item = modulestore().get_item(usage_key)
        if not module_item.hide_from_toc and module_item.is_entrance_exam:
            # Here we are looking for entrance exam module/chapter in required_content.
            # If module_item is an entrance exam chapter then set and return its info e.g. exam chapter, exam state.
            exam_chapter = module_item
            is_exam_passed = False
            break
    return exam_chapter, is_exam_passed


def get_required_content(course, user):
    """
    Queries milestones subsystem to see if the specified course is gated on one or more milestones,
    and if those milestones can be fulfilled via completion of a particular course content module
    """
    required_content = []
    if settings.FEATURES.get('MILESTONES_APP', False):
        # Get all of the outstanding milestones for this course, for this user
        try:
            milestone_paths = get_course_milestones_fulfillment_paths(
                unicode(course.id),
                serialize_user(user)
            )
        except InvalidMilestoneRelationshipTypeException:
            return required_content

        # For each outstanding milestone, see if this content is one of its fulfillment paths
        for path_key in milestone_paths:
            milestone_path = milestone_paths[path_key]
            if milestone_path.get('content') and len(milestone_path['content']):
                for content in milestone_path['content']:
                    required_content.append(content)

    # check if required_content has any entrance exam
    # and user is allowed to skip it then remove it from required content
    if required_content and getattr(course, 'entrance_exam_enabled', False) and \
            can_skip_entrance_exam(user, course):
        descriptors = [modulestore().get_item(UsageKey.from_string(content)) for content in required_content]
        entrance_exam_contents = [unicode(descriptor.location)
                                  for descriptor in descriptors if descriptor.is_entrance_exam]
        required_content = list(set(required_content) - set(entrance_exam_contents))
    return required_content
