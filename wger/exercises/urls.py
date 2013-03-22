from django.conf.urls import patterns, url
from django.contrib.auth.decorators import permission_required

from wger.exercises.views import exercises
from wger.exercises.views import comments
from wger.exercises.views import categories
from wger.exercises.views import muscles

urlpatterns = patterns('wger.exercises.views',

    # Exercises
    url(r'^overview/$', 'exercises.overview'),

    url(r'^search/$', 'exercises.search'),
    url(r'^(?P<id>\d+)/view/(?P<slug>[-\w]+)/$', 'exercises.view'),
    url(r'^(?P<id>\d+)/view/$', 'exercises.view'),
    url(r'^add/$',
        permission_required('exercises.change_exercise')(exercises.ExerciseAddView.as_view()),
        name='exercise-add'),
    url(r'^(?P<pk>\d+)/edit/$',
        permission_required('exercises.change_exercise')(exercises.ExerciseUpdateView.as_view()),
        name='exercise-edit'),
    url(r'^(?P<pk>\d+)/delete/$',
        permission_required('exercises.change_exercise')(exercises.ExerciseDeleteView.as_view()),
        name='exercise-delete'),

    # Muscles
    url(r'^muscle/overview/$',
        muscles.MuscleListView.as_view(),
        name='muscle-overview'),
    url(r'^muscle/add/$',
        permission_required('exercises.change_exercise')(muscles.MuscleAddView.as_view()),
        name='muscle-add'),
    url(r'^muscle/(?P<pk>\d+)/edit/$',
        permission_required('exercises.change_exercise')(muscles.MuscleUpdateView.as_view()),
        name='muscle-edit'),
    url(r'^muscle/(?P<pk>\d+)/delete/$',
        permission_required('exercises.change_exercise')(muscles.MuscleDeleteView.as_view()),
        name='muscle-delete'),

    # Comments
    url(r'^(?P<exercise_pk>\d+)/comment/add/$',
        permission_required('exercises.change_exercise')(comments.ExerciseCommentAddView.as_view()),
        name='exercisecomment-add'),
    url(r'^comment/(?P<pk>\d+)/edit/$',
        permission_required('exercises.change_exercise')(comments.ExerciseCommentEditView.as_view()),
        name='exercisecomment-edit'),
    url(r'^comment/(?P<id>\d+)/delete/$',
        'comments.delete',
        name='exercisecomment-delete'),

    # Categories
    url(r'^category/(?P<pk>\d+)/edit/$',
        permission_required('exercises.change_exercise')(categories.ExerciseCategoryUpdateView.as_view()),
        name='exercisecategory-edit'),
    url(r'^category/add/$',
        permission_required('exercises.change_exercise')(categories.ExerciseCategoryAddView.as_view()),
        name='exercisecategory-add'),
    url(r'^category/(?P<pk>\d+)/delete/$',
        permission_required('exercises.change_exercise')(categories.ExerciseCategoryDeleteView.as_view()),
        name='exercisecategory-delete'),
)
