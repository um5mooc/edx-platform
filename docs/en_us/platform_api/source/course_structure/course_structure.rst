##############################
Courses API Module
##############################


.. _Get a List of Courses:

**************************
Get a List of Courses
**************************

.. autoclass:: course_structure_api.v0.views.CourseList

**Example response**

.. code-block:: json

    {
        "count": 809, 
        "next": "https://courses.stage.edx.org/api/course_structure/v0/courses/?page=3", 
        "previous": "https://courses.stage.edx.org/api/course_structure/v0/courses/?page=1",  
        "num_pages": 81, 
        "results": [
            {
                "id": "ANUx/ANU-ASTRO1x/1T2014", 
                "name": "Greatest Unsolved Mysteries of the Universe", 
                "category": "course", 
                "org": "ANUx", 
                "run": "1T2014", 
                "course": "ANU-ASTRO1x", 
                "uri": "https://courses.stage.edx.org/api/course_structure/v0/courses/ANUx/ANU-ASTRO1x/1T2014/", 
                "image_url": "/c4x/ANUx/ANU-ASTRO1x/asset/dome_dashboard.jpg", 
                "start": "2014-03-24T18:30:00Z", 
                "end": null
            }, 
            {
                "id": "ANUx/ANU-ASTRO4x/1T2015", 
                "name": "COSMOLOGY", 
                "category": "course", 
                "org": "ANUx", 
                "run": "1T2015", 
                "course": "ANU-ASTRO4x", 
                "uri": "https://courses.stage.edx.org/api/course_structure/v0/courses/ANUx/ANU-ASTRO4x/1T2015/", 
                "image_url": "/c4x/ANUx/ANU-ASTRO4x/asset/ASTRO4x_dashboard_image.jpeg", 
                "start": "2015-02-03T00:00:00Z", 
                "end": "2015-04-28T23:30:00Z"
            }
            . . .
        ]
    }


