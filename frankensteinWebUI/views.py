# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.shortcuts import render, redirect
from django.views.decorators.csrf import csrf_exempt
from django.http import HttpResponse
from django.utils.http import urlencode
from django import forms

import os
import json
import glob
import hashlib
from binascii import hexlify, unhexlify
import traceback

from core.project import Project #TODO rename

#TODO move to forms.py
class projectNameForm(forms.Form):
    projectName = forms.CharField(max_length=100, help_text='Project Name', validators=[lambda x: not x])

class editConfigForm(forms.Form):
    projectName = forms.CharField(max_length=100, help_text='Project Name', validators=[lambda x: not x], widget=forms.HiddenInput())
    toolchain = forms.CharField(max_length=100, help_text='Toolchain', validators=[lambda x: not x])
    emulationCFlags = forms.CharField(max_length=1000, help_text='emulationCFlags', validators=[lambda x: not x])
    emulationCodeBase = forms.CharField(help_text="emulationCodeBase", validators=[lambda x: not int(x,16)])
    patchCFlags = forms.CharField(max_length=1000, help_text='patchCFlags', validators=[lambda x: not x])
    patchCodeBase = forms.CharField(help_text="patchCodeBase", validators=[lambda x: not int(x,16)])

class editGroupForm(forms.Form):
    projectName = forms.CharField(max_length=100, help_text='Project Name', validators=[lambda x: not x], widget=forms.HiddenInput())
    oldGroupName = forms.CharField(max_length=100, help_text='Old Group Name', validators=[lambda x: not x])
    newGroupName = forms.CharField(max_length=100, help_text='New Group Name', validators=[lambda x: not x])
    active = forms.BooleanField(help_text="Is Segment Active", required=False)

class editSegmentForm(forms.Form):
    projectName = forms.CharField(max_length=100, help_text='Project Name', validators=[lambda x: not x], widget=forms.HiddenInput())
    oldSegmentName = forms.CharField(max_length=100, help_text='Old Segment Name', validators=[lambda x: not x])
    oldGroupName = forms.CharField(max_length=100, help_text='Old Group Name', validators=[lambda x: not x])
    newSegmentName = forms.CharField(max_length=100, help_text='New Segment Name', validators=[lambda x: not x])
    newGroupName = forms.CharField(max_length=100, help_text='New Group Name', validators=[lambda x: not x])
    addr = forms.CharField(help_text="Segment Address", validators=[lambda x: not int(x,16)])
    active = forms.BooleanField(help_text="Is Segment Active", required=False)

class editSymbolForm(forms.Form):
    projectName = forms.CharField(max_length=100, help_text='Project Name', validators=[lambda x: not x], widget=forms.HiddenInput())
    oldSymbolName = forms.CharField(max_length=100, validators=[lambda x: not x], widget=forms.HiddenInput())
    oldGroupName = forms.CharField(max_length=100, validators=[lambda x: not x], widget=forms.HiddenInput())
    newSymbolName = forms.CharField(max_length=100, help_text='Symbol Name', validators=[lambda x: not x])
    newGroupName = forms.CharField(max_length=100, help_text='Group Name', validators=[lambda x: not x])
    value = forms.CharField(help_text="Value", validators=[lambda x: not int(x,16)])

class loadSegmentForm(forms.Form):
    projectName = forms.CharField(max_length=100, help_text='Project Name', validators=[lambda x: not x], widget=forms.HiddenInput())
    segment = forms.FileField(help_text='File', validators=[lambda x: not x])
    addr = forms.CharField(help_text="Segment Address", validators=[lambda x: not int(x,16)])
    groupName = forms.CharField(max_length=100, help_text='Segment Group', validators=[lambda x: not x])

class loadELFForm(forms.Form):
    projectName = forms.CharField(max_length=100, help_text='Project Name', validators=[lambda x: not x], widget=forms.HiddenInput())
    elf = forms.FileField(help_text='File', validators=[lambda x: not x])
    loadSymbols = forms.BooleanField(help_text="Load Symbols", required=False, initial=True)
    loadSegments = forms.BooleanField(help_text="Load Segments", required=False, initial=True)
    groupName = forms.CharField(max_length=100, help_text='Segment Group', validators=[lambda x: not x])

class loadIdbForm(forms.Form):
    projectName = forms.CharField(max_length=100, help_text='Project Name', validators=[lambda x: not x], widget=forms.HiddenInput())
    idb = forms.FileField(help_text='File', validators=[lambda x: not x])
    loadFunctions = forms.BooleanField(help_text="Load Functions", required=False, initial=True)
    loadSegments = forms.BooleanField(help_text="Load Segments", required=False, initial=True)



"""
Project Management
"""
def getProjectByName(projectName):
    projectPath = "projects/"+os.path.basename(projectName)
    return Project(projectPath)

def index(request):
    projects = glob.glob("projects/*/project.json")
    projects = map(lambda x: os.path.basename(os.path.dirname(x)), projects)
    context = {"projects": projects}
    return render(request, 'project/index.html', context)

def editProject(request):
    projectName = request.GET["projectName"]
    if not os.path.isfile("projects/%s/project.json"):
        redirect("/")

    project = getProjectByName(projectName)

    #segments = sorted(project.cfg["segments"].iteritems(), key=lambda x: x[1]["addr"])
    context = {"projectName": projectName, "project": project}
    context['projectNameForm'] = projectNameForm({"projectName": projectName})
    context['editSegmentForm'] = editSegmentForm({"projectName": projectName})
    context['loadSegmentForm'] = loadSegmentForm({"projectName": projectName})
    context['loadELFForm'] = loadELFForm({"projectName": projectName})
    context['loadIdbForm'] = loadIdbForm({"projectName": projectName})

    return render(request, 'project/editProject.html', context)


def newProject(request):
    if request.method == 'POST':
        form = projectNameForm(request.POST)
        if form.is_valid():
            project = getProjectByName(form.cleaned_data["projectName"])
            project.save()
            return redirect("/")
    else:
        form = projectNameForm()

    context = {}
    context['projectNameForm'] = form
    return render(request, 'project/newProject.html', context)

def getProjectCfg(request):
    projectName = request.GET["projectName"]
    if not os.path.isfile("projects/%s/project.json"):
        redirect("/")

    project = getProjectByName(projectName)
    return HttpResponse(json.dumps(project.cfg))

def projectSanityCheck(request):
    projectName = request.GET["projectName"]
    if not os.path.isfile("projects/%s/project.json"):
        redirect("/")

    try:
        project = getProjectByName(projectName)
        project.sanity_check()
        return HttpResponse(project.error_msgs)
    except:
        return HttpResponse(traceback.format_exc())
    


"""
Config/Group/Segment/Symbol Management
"""

def editConfig(request):
    if request.method == 'POST':
        form = editConfigForm(request.POST)
        if form.is_valid():
            projectName = form.cleaned_data["projectName"]
            project = getProjectByName(projectName)
            succsess = True
            if not project.set_toolchain(form.cleaned_data["toolchain"]):
                succsess = False

            if not project.set_emulation_config(form.cleaned_data["emulationCFlags"], int(form.cleaned_data["emulationCodeBase"], 16)):
                succsess = False
            if not project.set_patch_config(form.cleaned_data["patchCFlags"], int(form.cleaned_data["patchCodeBase"], 16)):
                succsess = False

            print succsess
            if succsess:
                project.save()

            return HttpResponse(project.error_msgs)
    else:
        form = editConfigForm()

    return HttpResponse(str(form.errors))

def editGroup(request):
    if request.method == 'POST':
        form = editGroupForm(request.POST)
        if form.is_valid():
            projectName = form.cleaned_data["projectName"]
            oldGroupName = form.cleaned_data["oldGroupName"]
            newGroupName = form.cleaned_data["newGroupName"]
            active = form.cleaned_data["active"]

            project = getProjectByName(projectName)
            if "actionUpdate" in request.POST:
                project.update_group(oldGroupName, newGroupName)
                project.set_active_group(newGroupName, active)
                project.save()
            if "actionDelete" in request.POST:
                project.delete_group(oldGroupName)
                project.save()

            return HttpResponse(project.error_msgs)
    else:
        form = editGroupForm()

    return HttpResponse(str(form.errors))

def editSegment(request):
    if request.method == 'POST':
        form = editSegmentForm(request.POST)
        if form.is_valid():
            projectName = form.cleaned_data["projectName"]
            oldSegmentName = form.cleaned_data["oldSegmentName"]
            oldGroupName = form.cleaned_data["oldGroupName"]
            newSegmentName = form.cleaned_data["newSegmentName"]
            newGroupName = form.cleaned_data["newGroupName"]
            active = form.cleaned_data["active"]
            addr = int(form.cleaned_data["addr"], 16)

            project = getProjectByName(projectName)
            if "actionUpdate" in request.POST:
                project.update_segment(oldGroupName, oldSegmentName, newGroupName, newSegmentName, addr)
                project.set_active_segment(newGroupName, newSegmentName, active)
                project.save()
            if "actionDelete" in request.POST:
                project.delete_segment(oldGroupName, oldSegmentName)
                project.save()

            return HttpResponse(project.error_msgs)
    else:
        form = editSegmentForm()

    return HttpResponse(str(form.errors))

def editSymbol(request):
    if request.method == 'POST':
        form = editSymbolForm(request.POST)
        if form.is_valid():
            projectName = form.cleaned_data["projectName"]
            oldSymbolName = form.cleaned_data["oldSymbolName"]
            oldGroupName = form.cleaned_data["oldGroupName"]
            newSymbolName = form.cleaned_data["newSymbolName"]
            newGroupName = form.cleaned_data["newGroupName"]
            value = form.cleaned_data["value"]

            project = getProjectByName(projectName)
            if "actionAdd" in request.POST:
                if project.add_symbol(newGroupName, newSymbolName, int(value, 16)):
                    project.save()

            if "actionUpdate" in request.POST:
                if project.update_symbol(oldGroupName, oldSymbolName, newGroupName, newSymbolName, int(value, 16)):
                    project.save()

            if "actionDelete" in request.POST:
                if project.delete_symbol(oldGroupName, oldSymbolName):
                    project.save()

            return HttpResponse(project.error_msgs)
    else:
        form = editSymbolForm()

    return HttpResponse(str(form.errors))


"""
Import Data
"""

def loadELF(request):
    if request.method == 'POST':
        form = loadELFForm(request.POST, request.FILES)

        if form.is_valid():
            projectName = form.cleaned_data["projectName"]
            loadSegments = form.cleaned_data["loadSegments"]
            loadSymbols = form.cleaned_data["loadSymbols"]
            groupName = form.cleaned_data["groupName"]
            groupName = "" if groupName == "Create New" else groupName


            try:
                fname = os.path.basename(str(request.FILES['elf']))
                with open('/tmp/%s' % fname, 'wb+') as f:
                    for chunk in request.FILES['elf'].chunks():
                            f.write(chunk)

                project = getProjectByName(form.cleaned_data["projectName"])
                project.load_elf("/tmp/%s" % fname, load_segments=loadSegments, load_symbols=loadSymbols, group=groupName)
                project.save()

                return HttpResponse(project.error_msgs)
            except:
                return HttpResponse(traceback.format_exc())
                
    else:
        form = loadELFForm()

    context = {}
    return HttpResponse(str(form.errors))

def loadIdb(request):
    if request.method == 'POST':
        form = loadIdbForm(request.POST, request.FILES)

        if form.is_valid():
            projectName = form.cleaned_data["projectName"]
            loadSegments = form.cleaned_data["loadSegments"]
            loadFunctions = form.cleaned_data["loadFunctions"]
            fname = os.path.basename(str(request.FILES['idb']))
            with open('/tmp/%s' % fname, 'wb+') as f:
                for chunk in request.FILES['idb'].chunks():
                        f.write(chunk)

            try:
                project = getProjectByName(form.cleaned_data["projectName"])
                pe.project.load_idb("/tmp/%s" % fname, load_segments=loadSegments, load_functions=loadFunctions)
                pe.project.save()

                return HttpResponse(project.error_msgs)
            except:
                return HttpResponse(traceback.format_exc())
    else:
        form = loadIdbForm()

    return HttpResponse(str(form.errors))


def loadSegment(request):
    if request.method == 'POST':
        form = loadSegmentForm(request.POST, request.FILES)

        if form.is_valid():
            projectName = form.cleaned_data["projectName"]
            addr = int(form.cleaned_data["addr"], 16)
            groupName = form.cleaned_data["groupName"]
            data = request.FILES['segment'].read()
            fname = os.path.basename(str(request.FILES['segment']))
            segmentName = "%s_0x%x" % (fname, addr)

            try:
                project = getProjectByName(form.cleaned_data["projectName"])
                project.add_segment(groupName, segmentName, addr, data)
                project.save()

                return HttpResponse(project.error_msgs)
            except:
                return HttpResponse(traceback.format_exc())
    else:
        form = loadELFForm()

    return HttpResponse(str(form.errors))