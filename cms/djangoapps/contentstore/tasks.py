"""
This file contains celery tasks for contentstore views
"""

from celery.task import task
from celery.utils.log import get_task_logger
from django.contrib.auth.models import User
import json
import logging
from xmodule.modulestore.django import modulestore
from xmodule.course_module import CourseFields

from xmodule.modulestore.courseware_index import CoursewareSearchIndexer, SearchIndexingError
from xmodule.modulestore.exceptions import DuplicateCourseError, ItemNotFoundError
from course_action_state.models import CourseRerunState
from contentstore.utils import initialize_permissions
from opaque_keys.edx.keys import CourseKey, UsageKey


LOGGER = get_task_logger(__name__)
FULL_COURSE_REINDEX_THRESHOLD = 1


@task()
def rerun_course(source_course_key_string, destination_course_key_string, user_id, fields=None):
    """
    Reruns a course in a new celery task.
    """
    try:
        # deserialize the payload
        source_course_key = CourseKey.from_string(source_course_key_string)
        destination_course_key = CourseKey.from_string(destination_course_key_string)
        fields = deserialize_fields(fields) if fields else None

        # use the split modulestore as the store for the rerun course,
        # as the Mongo modulestore doesn't support multiple runs of the same course.
        store = modulestore()
        with store.default_store('split'):
            store.clone_course(source_course_key, destination_course_key, user_id, fields=fields)

        # set initial permissions for the user to access the course.
        initialize_permissions(destination_course_key, User.objects.get(id=user_id))

        # update state: Succeeded
        CourseRerunState.objects.succeeded(course_key=destination_course_key)
        return "succeeded"

    except DuplicateCourseError as exc:
        # do NOT delete the original course, only update the status
        CourseRerunState.objects.failed(course_key=destination_course_key)
        logging.exception(u'Course Rerun Error')
        return "duplicate course"

    # catch all exceptions so we can update the state and properly cleanup the course.
    except Exception as exc:  # pylint: disable=broad-except
        # update state: Failed
        CourseRerunState.objects.failed(course_key=destination_course_key)
        logging.exception(u'Course Rerun Error')

        try:
            # cleanup any remnants of the course
            modulestore().delete_course(destination_course_key, user_id)
        except ItemNotFoundError:
            # it's possible there was an error even before the course module was created
            pass

        return "exception: " + unicode(exc)


def deserialize_fields(json_fields):
    fields = json.loads(json_fields)
    for field_name, value in fields.iteritems():
        fields[field_name] = getattr(CourseFields, field_name).from_json(value)
    return fields


@task()
def update_search_index(course_id, item_ids=None):
    """ Updates course search index. """
    def index_location(location):
        """ Adds location to the courseware search index """
        CoursewareSearchIndexer.add_to_search_index(modulestore(), location, delete=False, raise_on_error=True)

    try:
        course_key = CourseKey.from_string(course_id)
        if item_ids and len(item_ids) <= FULL_COURSE_REINDEX_THRESHOLD:
            for item_id in item_ids:
                item_key = UsageKey.from_string(item_id).replace(run=course_key.run)
                index_location(item_key)
        else:
            index_location(course_key)

    except SearchIndexingError as exc:
        if item_ids:
            LOGGER.error(
                'Search indexing error for items %s in course %s - %s',
                ','.join(item_ids),
                course_id,
                unicode(exc)
            )
        else:
            LOGGER.error('Search indexing error for complete course %s - %s', course_id, unicode(exc))
    else:
        if item_ids:
            LOGGER.debug('Search indexing successful for items %s in course %s', ','.join(item_ids), course_id)
        else:
            LOGGER.debug('Search indexing successful for complete course %s', course_id)
