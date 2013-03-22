# -*- coding: utf-8 -*-

# This file is part of Workout Manager.
#
# Workout Manager is free software: you can redistribute it and/or modify
# it under the terms of the GNU Affero General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# Workout Manager is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU Affero General Public License

import logging
import uuid

from django.template import RequestContext
from django.shortcuts import render_to_response
from django.shortcuts import get_object_or_404
from django.http import HttpResponse
from django.http import HttpResponseRedirect
from django.http import HttpResponseForbidden
from django.core.context_processors import csrf
from django.core.urlresolvers import reverse
from django.utils.translation import ugettext as _
from django.utils.translation import ugettext_lazy
from django.db import models

from django.contrib.auth.decorators import login_required

from django.views.generic import DeleteView
from django.views.generic import CreateView
from django.views.generic import UpdateView

from wger.manager.models import TrainingSchedule
from wger.manager.models import Day
from wger.manager.models import Set
from wger.manager.models import Setting

from wger.exercises.models import Exercise

from wger.manager.forms import SetForm

from wger.workout_manager.generic_views import YamlFormMixin
from wger.workout_manager.generic_views import YamlDeleteMixin

logger = logging.getLogger('workout_manager.custom')


# ************************
# Set functions
# ************************


class SetCreateView(YamlFormMixin, CreateView):
    model = Set
    form_class = SetForm
    template_name = 'set/edit.html'

    def dispatch(self, request, *args, **kwargs):
        '''
        Check that the user owns the workout
        '''
        day = get_object_or_404(Day, pk=kwargs['day_id'])
        if day.get_owner_object().user == request.user:
            self.day = day
            return super(SetCreateView, self).dispatch(request, *args, **kwargs)
        else:
            return HttpResponseForbidden()

    def get_success_url(self):
        return reverse('wger.manager.views.workout.view',
                       kwargs={'id': self.day.training.id})

    def form_valid(self, form):
        '''
        Manually set the order
        '''
        max_order = self.day.set_set.select_related().aggregate(models.Max('order'))
        form.instance.order = (max_order['order__max'] or 0) + 1
        form.instance.exerciseday = self.day
        return super(SetCreateView, self).form_valid(form)

    def get_context_data(self, **kwargs):
        '''
        Send some additional data to the template
        '''
        context = super(SetCreateView, self).get_context_data(**kwargs)
        context['form_action'] = reverse('set-add', kwargs={'day_id': self.day.id})
        return context


@login_required
def delete(request, pk):
    '''
    Deletes the given set
    '''

    # Load the set
    set_obj = get_object_or_404(Set, pk=pk)

    # Check if the user is the owner of the object
    if set_obj.get_owner_object().user == request.user:
        set_obj.delete()
        return HttpResponseRedirect(reverse('wger.manager.views.workout.view',
                                            kwargs={'id': set_obj.get_owner_object().id}))
    else:
        return HttpResponseForbidden()


@login_required
def api_edit_set(request):
    '''
    Allows to edit the order of the sets via an AJAX call
    '''

    if request.is_ajax():

        # Set the order of the reps
        if request.GET.get('do') == 'set_order':
            day_id = request.GET.get('day_id')
            new_set_order = request.GET.get('order')

            order = 0
            for i in new_set_order.strip(',').split(','):
                set_id = i.split('-')[1]
                order += 1

                set_obj = get_object_or_404(Set, pk=set_id, exerciseday=day_id)

                # Check if the user is the owner of the object
                if set_obj.exerciseday.training.user == request.user:
                    set_obj.order = order
                    set_obj.save()
                else:
                    return HttpResponseForbidden()

            return HttpResponse(_('Success'))

        # This part is responsible for the in-place editing of the sets and settings
        if request.GET.get('do') == 'edit_set':
            template_data = {}
            template_data.update(csrf(request))

            # Load the objects
            set_id = request.GET.get('set')
            workout_set = get_object_or_404(Set, pk=set_id)
            template_data['set'] = workout_set

            exercise_id = request.GET.get('exercise')
            exercise = get_object_or_404(Exercise, pk=exercise_id)

            # Allow editing settings/repetitions that are not yet associated with the set
            #
            # We calculate here how many are there already [.filter(...)] and how many there could
            # be at all (workout_set.sets)
            current_settings = exercise.setting_set.filter(set_id=set_id).count()
            diff = int(workout_set.sets) - current_settings

            # If there are 'free slots', create some UUIDs for them, this gives them unique form
            # names in the HTML and makes our lifes easier
            new_settings = []
            if diff > 0:

                # Note: use UUIDs version 1 because they are monotonously increasing
                #       and the order of the fields later is important
                new_settings = [uuid.uuid1() for i in range(0, diff)]
            template_data['new_settings'] = new_settings

            # Process request
            if request.method == 'POST':

                new_exercise_id = request.POST.get('current_exercise')
                new_exercise = get_object_or_404(Exercise, pk=new_exercise_id)

                # When there is more than one exercise per set, we need to manually set and replace
                # the IDs here, otherwise they get lost
                request_copy = request.POST
                request_copy = request_copy.copy()

                exercise_list = [i for i in request_copy.getlist('exercises') if i != exercise_id]
                request_copy.setlist('exercises', exercise_list)
                request_copy.update({'exercises': new_exercise_id})

                set_form = SetForm(request_copy, instance=workout_set)

                if set_form.is_valid():
                    set_form.save()

                # Init a counter for the order in case we have to set it for new settings
                # We don't actually care how hight the counter actually is, as long as the new
                # settings get a number that puts them at the end
                order_counter = 1
                new_settings = []

                # input fields for settings  'setting-x, setting-y, etc.',
                #              new settings: 'new-setting-UUID1, new-setting-UUID2, etc.'
                for i in request.POST:
                    order_counter += 1

                    # old settings, update
                    if i.startswith('setting'):
                        setting_id = int(i.split('-')[-1])
                        setting = get_object_or_404(Setting, pk=setting_id)

                        # Check if the new value is empty (the user wants the setting deleted)
                        # We don't check more, if the user enters a string, it won't be converted
                        # and nothing will happen
                        if request.POST[i] == '':
                            setting.delete()
                        else:
                            reps = int(request.POST[i])
                            setting.reps = reps
                            setting.exercise = new_exercise
                            setting.save()

                    # New settings, put in a list, see below
                    if i.startswith('new-setting') and request.POST[i]:

                        new_settings.append(i)

                # new settings, sort by name (important to keep the order as
                # it was inputted in the website),create object and save
                new_settings.sort()
                for i in new_settings:
                    reps = int(request.POST[i])

                    setting = Setting()
                    setting.exercise = new_exercise
                    setting.set = workout_set
                    setting.reps = reps
                    setting.order = order_counter
                    setting.save()

            template_data['exercise'] = exercise

            return render_to_response('setting/ajax_edit.html',
                                      template_data,
                                      context_instance=RequestContext(request))
