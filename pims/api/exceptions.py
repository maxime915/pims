# * Copyright (c) 2020. Authors: see NOTICE file.
# *
# * Licensed under the Apache License, Version 2.0 (the "License");
# * you may not use this file except in compliance with the License.
# * You may obtain a copy of the License at
# *
# *      http://www.apache.org/licenses/LICENSE-2.0
# *
# * Unless required by applicable law or agreed to in writing, software
# * distributed under the License is distributed on an "AS IS" BASIS,
# * WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# * See the License for the specific language governing permissions and
# * limitations under the License.

from connexion import ProblemException

from pims.api.utils.parameter import path2filepath


class FilepathNotFoundProblem(ProblemException):
    def __init__(self, filepath):
        filepath = path2filepath(filepath) if type(filepath) is not str else filepath
        title = 'Filepath not found'
        detail = 'The filepath {} does not exist.'.format(filepath)
        super(FilepathNotFoundProblem, self).__init__(status=404, title=title, detail=detail)


class NoAppropriateRepresentationProblem(ProblemException):
    def __init__(self, filepath, representation=None):
        filepath = path2filepath(filepath) if type(filepath) is not str else filepath
        title = 'No appropriate representation found'
        detail = 'The filepath {} does not have an appropriate representation'.format(filepath)
        if representation:
            detail += ' (expected {})'.format(representation)
        super(NoAppropriateRepresentationProblem, self).__init__(status=400, title=title, detail=detail)


class NotADirectoryProblem(ProblemException):
    def __init__(self, filepath):
        filepath = path2filepath(filepath) if type(filepath) is not str else filepath
        title = 'Not a directory'
        detail = 'The filepath {} is not a directory'.format(filepath)
        super(NotADirectoryProblem, self).__init__(status=400, title=title, detail=detail)


class NoMatchingFormatProblem(ProblemException):
    def __init__(self, filepath):
        filepath = path2filepath(filepath) if type(filepath) is not str else filepath
        title = "No matching format found"
        detail = "The filepath {} is recognized by any of the available formats.".format(filepath)
        super(NoMatchingFormatProblem, self).__init__(status=400, title=title, detail=detail)


class FormatNotFoundProblem(ProblemException):
    def __init__(self, format_id):
        title = 'Format not found'
        detail = 'The format {} does not exist.'.format(format_id)
        super(FormatNotFoundProblem, self).__init__(status=404, title=title, detail=detail)


class ColormapNotFoundProblem(ProblemException):
    def __init__(self, colormap_id):
        title = 'Colormap not found'
        detail = 'The colormap {} does not exist.'.format(colormap_id)
        super(ColormapNotFoundProblem, self).__init__(status=404, title=title, detail=detail)


def check_path_existence(path):
    if not path.exists():
        raise FilepathNotFoundProblem(path)


def check_path_is_single(path):
    if not path.is_single():
        raise NoAppropriateRepresentationProblem(path)


def check_representation_existence(path):
    if not path.exists():
        raise NoAppropriateRepresentationProblem(path)